from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from collections import OrderedDict, deque
from collections.abc import (
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Collection,
    Generator,
    Iterable,
    Iterator,
    Mapping,
)
from contextlib import asynccontextmanager, contextmanager, nullcontext, suppress
from dataclasses import dataclass, field
from enum import StrEnum
from functools import partial, partialmethod, singledispatchmethod, update_wrapper
from inspect import (
    Signature,
    isasyncgenfunction,
    isclass,
    iscoroutinefunction,
    isgeneratorfunction,
    markcoroutinefunction,
)
from inspect import signature as inspect_signature
from logging import Logger, getLogger
from types import MethodType
from typing import (
    Any,
    AsyncContextManager,
    ClassVar,
    ContextManager,
    Literal,
    NamedTuple,
    Protocol,
    Self,
    overload,
    runtime_checkable,
)

from injection._core.common.asynchronous import (
    AsyncCaller,
    Caller,
    SimpleAwaitable,
    SyncCaller,
)
from injection._core.common.event import Event, EventChannel, EventListener
from injection._core.common.invertible import Invertible, SimpleInvertible
from injection._core.common.key import new_short_key
from injection._core.common.lazy import Lazy, alazy, lazy
from injection._core.common.type import (
    InputType,
    TypeInfo,
    get_return_types,
    get_yield_hint,
    standardize_types,
)
from injection._core.injectables import (
    AsyncCMScopedInjectable,
    CMScopedInjectable,
    Injectable,
    ScopedInjectable,
    ScopedSlotInjectable,
    ShouldBeInjectable,
    SimpleScopedInjectable,
    SingletonInjectable,
    TransientInjectable,
)
from injection._core.slots import SlotKey
from injection.exceptions import (
    ModuleError,
    ModuleLockError,
    ModuleNotUsedError,
    NoInjectable,
    SkipInjectable,
)

"""
Events
"""


@dataclass(frozen=True, slots=True)
class LocatorEvent(Event, ABC):
    locator: Locator


@dataclass(frozen=True, slots=True)
class LocatorDependenciesUpdated[T](LocatorEvent):
    classes: Collection[InputType[T]]
    mode: Mode

    def __str__(self) -> str:
        length = len(self.classes)
        formatted_types = ", ".join(f"`{cls}`" for cls in self.classes)
        return (
            f"{length} dependenc{'ies' if length > 1 else 'y'} have been "
            f"updated{f': {formatted_types}' if formatted_types else ''}."
        )


@dataclass(frozen=True, slots=True)
class ModuleEvent(Event, ABC):
    module: Module


@dataclass(frozen=True, slots=True)
class ModuleEventProxy(ModuleEvent):
    event: Event

    def __str__(self) -> str:
        return f"`{self.module}` has propagated an event: {self.origin}"

    @property
    def history(self) -> Iterator[Event]:
        if isinstance(self.event, ModuleEventProxy):
            yield from self.event.history

        yield self.event

    @property
    def origin(self) -> Event:
        return next(self.history)


@dataclass(frozen=True, slots=True)
class ModuleAdded(ModuleEvent):
    module_added: Module
    priority: Priority

    def __str__(self) -> str:
        return f"`{self.module}` now uses `{self.module_added}`."


@dataclass(frozen=True, slots=True)
class ModuleRemoved(ModuleEvent):
    module_removed: Module

    def __str__(self) -> str:
        return f"`{self.module}` no longer uses `{self.module_removed}`."


@dataclass(frozen=True, slots=True)
class ModulePriorityUpdated(ModuleEvent):
    module_updated: Module
    priority: Priority

    def __str__(self) -> str:
        return (
            f"In `{self.module}`, the priority `{self.priority}` "
            f"has been applied to `{self.module_updated}`."
        )


"""
Broker
"""


@runtime_checkable
class Broker(Protocol):
    __slots__ = ()

    @abstractmethod
    def __getitem__[T](self, cls: InputType[T], /) -> Injectable[T]:
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, cls: InputType[Any], /) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_locked(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def unlock(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    async def all_ready(self) -> None:
        raise NotImplementedError


"""
Locator
"""


class Mode(StrEnum):
    FALLBACK = "fallback"
    NORMAL = "normal"
    OVERRIDE = "override"

    @property
    def rank(self) -> int:
        return tuple(type(self)).index(self)

    @classmethod
    def get_default(cls) -> Mode:
        return cls.NORMAL


type ModeStr = Literal["fallback", "normal", "override"]

type InjectableFactory[T] = Callable[[Caller[..., T]], Injectable[T]]


class Record[T](NamedTuple):
    injectable: Injectable[T]
    mode: Mode


@dataclass(repr=False, eq=False, kw_only=True, slots=True)
class Updater[T]:
    classes: Iterable[InputType[T]]
    injectable: Injectable[T]
    mode: Mode

    def make_record(self) -> Record[T]:
        return Record(self.injectable, self.mode)

    @classmethod
    def with_basics(
        cls,
        on: TypeInfo[T],
        /,
        injectable: Injectable[T],
        mode: Mode | ModeStr,
    ) -> Self:
        return cls(
            classes=get_return_types(on),
            injectable=injectable,
            mode=Mode(mode),
        )


@dataclass(repr=False, frozen=True, slots=True)
class Locator(Broker):
    __records: dict[InputType[Any], Record[Any]] = field(
        default_factory=dict,
        init=False,
    )
    __channel: EventChannel = field(
        default_factory=EventChannel,
        init=False,
    )

    def __getitem__[T](self, cls: InputType[T], /) -> Injectable[T]:
        for input_class in self.__standardize_inputs((cls,)):
            try:
                record = self.__records[input_class]
            except KeyError:
                continue

            return record.injectable

        raise NoInjectable(cls)

    def __contains__(self, cls: InputType[Any], /) -> bool:
        return any(
            input_class in self.__records
            for input_class in self.__standardize_inputs((cls,))
        )

    @property
    def is_locked(self) -> bool:
        return any(injectable.is_locked for injectable in self.__injectables)

    @property
    def __injectables(self) -> frozenset[Injectable[Any]]:
        return frozenset(record.injectable for record in self.__records.values())

    def update[T](self, updater: Updater[T]) -> Self:
        updater = self.__update_preprocessing(updater)
        record = updater.make_record()
        records = dict(self.__prepare_for_updating(updater.classes, record))

        if records:
            event = LocatorDependenciesUpdated(self, records.keys(), record.mode)

            with self.dispatch(event):
                self.__records.update(records)

        return self

    def unlock(self) -> Self:
        for injectable in self.__injectables:
            injectable.unlock()

        return self

    async def all_ready(self) -> None:
        for injectable in self.__injectables:
            if injectable.is_locked:
                continue

            with suppress(SkipInjectable):
                await injectable.aget_instance()

    def add_listener(self, listener: EventListener) -> Self:
        self.__channel.add_listener(listener)
        return self

    def dispatch(self, event: Event) -> ContextManager[None]:
        return self.__channel.dispatch(event)

    def __prepare_for_updating[T](
        self,
        classes: Iterable[InputType[T]],
        record: Record[T],
    ) -> Iterator[tuple[InputType[T], Record[T]]]:
        for cls in classes:
            try:
                existing = self.__records[cls]
            except KeyError:
                ...
            else:
                if not self.__keep_new_record(record, existing, cls):
                    continue

            yield cls, record

    @staticmethod
    def __keep_new_record[T](
        new: Record[T],
        existing: Record[T],
        cls: InputType[T],
    ) -> bool:
        new_mode, existing_mode = new.mode, existing.mode
        is_override = new_mode == Mode.OVERRIDE

        if new_mode == existing_mode and not is_override:
            raise RuntimeError(f"An injectable already exists for the class `{cls}`.")

        return is_override or new_mode.rank > existing_mode.rank

    @staticmethod
    def __standardize_inputs[T](
        classes: Iterable[InputType[T]],
    ) -> Iterable[InputType[T]]:
        return tuple(standardize_types(*classes, with_origin=True))

    @staticmethod
    def __update_preprocessing[T](updater: Updater[T]) -> Updater[T]:
        updater.classes = frozenset(standardize_types(*updater.classes))
        return updater


"""
Module
"""


class Priority(StrEnum):
    LOW = "low"
    HIGH = "high"

    @classmethod
    def get_default(cls) -> Priority:
        return cls.LOW


type PriorityStr = Literal["low", "high"]

type ContextManagerLikeRecipe[**P, T] = (
    Callable[P, ContextManager[T]] | Callable[P, AsyncContextManager[T]]
)
type GeneratorRecipe[**P, T] = (
    Callable[P, Generator[T, Any, Any]] | Callable[P, AsyncGenerator[T, Any]]
)
type Recipe[**P, T] = Callable[P, T] | Callable[P, Awaitable[T]]


@dataclass(eq=False, frozen=True, slots=True)
class Module(Broker, EventListener):
    name: str = field(default_factory=lambda: f"anonymous@{new_short_key()}")
    __channel: EventChannel = field(
        default_factory=EventChannel,
        init=False,
        repr=False,
    )
    __locator: Locator = field(
        default_factory=Locator,
        init=False,
        repr=False,
    )
    __loggers: list[Logger] = field(
        default_factory=lambda: [getLogger("python-injection")],
        init=False,
        repr=False,
    )
    __modules: OrderedDict[Module, None] = field(
        default_factory=OrderedDict,
        init=False,
        repr=False,
    )

    __instances: ClassVar[dict[str, Module]] = {}

    def __post_init__(self) -> None:
        self.__locator.add_listener(self)

    def __getitem__[T](self, cls: InputType[T], /) -> Injectable[T]:
        for broker in self.__brokers:
            with suppress(KeyError):
                return broker[cls]

        raise NoInjectable(cls)

    def __contains__(self, cls: InputType[Any], /) -> bool:
        return any(cls in broker for broker in self.__brokers)

    @property
    def is_locked(self) -> bool:
        return any(broker.is_locked for broker in self.__brokers)

    @property
    def __brokers(self) -> Iterator[Broker]:
        yield from self.__modules
        yield self.__locator

    def injectable[**P, T](
        self,
        wrapped: Recipe[P, T] | None = None,
        /,
        *,
        cls: InjectableFactory[T] = TransientInjectable,
        ignore_type_hint: bool = False,
        inject: bool = True,
        on: TypeInfo[T] = (),
        mode: Mode | ModeStr = Mode.get_default(),
    ) -> Any:
        def decorator(wp: Recipe[P, T]) -> Recipe[P, T]:
            factory = extract_caller(self.make_injected_function(wp) if inject else wp)
            injectable = cls(factory)  # type: ignore[arg-type]
            hints = on if ignore_type_hint else (wp, on)
            updater = Updater.with_basics(hints, injectable, mode)
            self.update(updater)
            return wp

        return decorator(wrapped) if wrapped else decorator

    singleton = partialmethod(injectable, cls=SingletonInjectable)

    def scoped[**P, T](
        self,
        scope_name: str,
        /,
        *,
        inject: bool = True,
        on: TypeInfo[T] = (),
        mode: Mode | ModeStr = Mode.get_default(),
    ) -> Any:
        def decorator(
            wrapped: Recipe[P, T] | GeneratorRecipe[P, T],
        ) -> Recipe[P, T] | GeneratorRecipe[P, T]:
            injectable_class: type[ScopedInjectable[Any, T]]
            wrapper: Recipe[P, T] | ContextManagerLikeRecipe[P, T]

            if isasyncgenfunction(wrapped):
                hint = get_yield_hint(wrapped)
                injectable_class = AsyncCMScopedInjectable
                wrapper = asynccontextmanager(wrapped)

            elif isgeneratorfunction(wrapped):
                hint = get_yield_hint(wrapped)
                injectable_class = CMScopedInjectable
                wrapper = contextmanager(wrapped)

            else:
                injectable_class = SimpleScopedInjectable
                hint = wrapper = wrapped  # type: ignore[assignment]

            hints = on if hint is None else (hint, on)
            self.injectable(
                wrapper,
                cls=partial(injectable_class, scope_name=scope_name),
                ignore_type_hint=True,
                inject=inject,
                on=hints,
                mode=mode,
            )
            return wrapped

        return decorator

    def should_be_injectable[T](self, wrapped: type[T] | None = None, /) -> Any:
        def decorator(wp: type[T]) -> type[T]:
            injectable = ShouldBeInjectable(wp)
            updater = Updater.with_basics(wp, injectable, Mode.FALLBACK)
            self.update(updater)
            return wp

        return decorator(wrapped) if wrapped else decorator

    def constant[T](
        self,
        wrapped: type[T] | None = None,
        /,
        *,
        on: TypeInfo[T] = (),
        mode: Mode | ModeStr = Mode.get_default(),
    ) -> Any:
        def decorator(wp: type[T]) -> type[T]:
            lazy_instance = lazy(wp)
            self.injectable(
                lambda: ~lazy_instance,
                ignore_type_hint=True,
                inject=False,
                on=(wp, on),
                mode=mode,
            )
            return wp

        return decorator(wrapped) if wrapped else decorator

    def set_constant[T](
        self,
        instance: T,
        on: TypeInfo[T] = (),
        *,
        alias: bool = False,
        mode: Mode | ModeStr = Mode.get_default(),
    ) -> Self:
        hints = on if alias else (type(instance), on)
        self.injectable(
            lambda: instance,
            ignore_type_hint=True,
            inject=False,
            on=hints,
            mode=mode,
        )
        return self

    def reserve_scoped_slot[T](
        self,
        cls: type[T],
        /,
        scope_name: str,
        *,
        mode: Mode | ModeStr = Mode.get_default(),
    ) -> SlotKey[T]:
        injectable = ScopedSlotInjectable(cls, scope_name)
        updater = Updater.with_basics(cls, injectable, mode)
        self.update(updater)
        return injectable.key

    def inject[**P, T](
        self,
        wrapped: Callable[P, T] | None = None,
        /,
        *,
        threadsafe: bool = False,
    ) -> Any:
        def decorator(wp: Callable[P, T]) -> Callable[P, T]:
            if isclass(wp):
                wp.__init__ = self.inject(wp.__init__, threadsafe=threadsafe)
                return wp

            return self.make_injected_function(wp, threadsafe)

        return decorator(wrapped) if wrapped else decorator

    @overload
    def make_injected_function[**P, T](
        self,
        wrapped: Callable[P, T],
        /,
        threadsafe: bool = ...,
    ) -> SyncInjectedFunction[P, T]: ...

    @overload
    def make_injected_function[**P, T](
        self,
        wrapped: Callable[P, Awaitable[T]],
        /,
        threadsafe: bool = ...,
    ) -> AsyncInjectedFunction[P, T]: ...

    def make_injected_function[**P, T](
        self,
        wrapped: Callable[P, T],
        /,
        threadsafe: bool = False,
    ) -> InjectedFunction[P, T]:
        metadata = InjectMetadata(wrapped, threadsafe)

        @metadata.task
        def listen() -> None:
            metadata.update(self)
            self.add_listener(metadata)

        if iscoroutinefunction(wrapped):
            return AsyncInjectedFunction(metadata)  # type: ignore[arg-type, return-value]

        return SyncInjectedFunction(metadata)

    def make_async_factory[T](
        self,
        wrapped: type[T],
        /,
        threadsafe: bool = False,
    ) -> Callable[..., Awaitable[T]]:
        factory: InjectedFunction[..., T] = self.make_injected_function(
            wrapped,
            threadsafe,
        )
        return factory.__inject_metadata__.acall

    async def afind_instance[T](self, cls: InputType[T]) -> T:
        injectable = self[cls]
        return await injectable.aget_instance()

    def find_instance[T](self, cls: InputType[T]) -> T:
        injectable = self[cls]
        return injectable.get_instance()

    @overload
    async def aget_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default,
    ) -> T | Default: ...

    @overload
    async def aget_instance[T](
        self,
        cls: InputType[T],
        default: None = ...,
    ) -> T | None: ...

    async def aget_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default | None = None,
    ) -> T | Default | None:
        try:
            return await self.afind_instance(cls)
        except (KeyError, SkipInjectable):
            return default

    @overload
    def get_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default,
    ) -> T | Default: ...

    @overload
    def get_instance[T](
        self,
        cls: InputType[T],
        default: None = ...,
    ) -> T | None: ...

    def get_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default | None = None,
    ) -> T | Default | None:
        try:
            return self.find_instance(cls)
        except (KeyError, SkipInjectable):
            return default

    @overload
    def aget_lazy_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default,
        *,
        cache: bool = ...,
    ) -> Awaitable[T | Default]: ...

    @overload
    def aget_lazy_instance[T](
        self,
        cls: InputType[T],
        default: None = ...,
        *,
        cache: bool = ...,
    ) -> Awaitable[T | None]: ...

    def aget_lazy_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default | None = None,
        *,
        cache: bool = False,
    ) -> Awaitable[T | Default | None]:
        if cache:
            return alazy(lambda: self.aget_instance(cls, default))

        function = self.make_injected_function(lambda instance=default: instance)
        metadata = function.__inject_metadata__.set_owner(cls)
        return SimpleAwaitable(metadata.acall)

    @overload
    def get_lazy_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default,
        *,
        cache: bool = ...,
    ) -> Invertible[T | Default]: ...

    @overload
    def get_lazy_instance[T](
        self,
        cls: InputType[T],
        default: None = ...,
        *,
        cache: bool = ...,
    ) -> Invertible[T | None]: ...

    def get_lazy_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default | None = None,
        *,
        cache: bool = False,
    ) -> Invertible[T | Default | None]:
        if cache:
            return lazy(lambda: self.get_instance(cls, default))

        function = self.make_injected_function(lambda instance=default: instance)
        metadata = function.__inject_metadata__.set_owner(cls)
        return SimpleInvertible(metadata.call)

    def update[T](self, updater: Updater[T]) -> Self:
        self.__locator.update(updater)
        return self

    def init_modules(self, *modules: Module) -> Self:
        for module in tuple(self.__modules):
            self.stop_using(module)

        for module in modules:
            self.use(module)

        return self

    def use(
        self,
        module: Module,
        *,
        priority: Priority | PriorityStr = Priority.get_default(),
    ) -> Self:
        if module is self:
            raise ModuleError("Module can't be used by itself.")

        if module in self.__modules:
            raise ModuleError(f"`{self}` already uses `{module}`.")

        priority = Priority(priority)
        event = ModuleAdded(self, module, priority)

        with self.dispatch(event):
            self.__modules[module] = None
            self.__move_module(module, priority)
            module.add_listener(self)

        return self

    def stop_using(self, module: Module) -> Self:
        event = ModuleRemoved(self, module)

        with suppress(KeyError):
            with self.dispatch(event):
                self.__modules.pop(module)
                module.remove_listener(self)

        return self

    @contextmanager
    def use_temporarily(
        self,
        module: Module,
        *,
        priority: Priority | PriorityStr = Priority.get_default(),
    ) -> Iterator[Self]:
        self.use(module, priority=priority)

        try:
            yield self
        finally:
            self.stop_using(module)

    def change_priority(self, module: Module, priority: Priority | PriorityStr) -> Self:
        priority = Priority(priority)
        event = ModulePriorityUpdated(self, module, priority)

        with self.dispatch(event):
            self.__move_module(module, priority)

        return self

    def unlock(self) -> Self:
        for broker in self.__brokers:
            broker.unlock()

        return self

    def load_profile(self, *names: str) -> ContextManager[Self]:
        modules = (self.from_name(name) for name in names)
        self.unlock().init_modules(*modules)

        @contextmanager
        def unload() -> Iterator[Self]:
            yield self
            self.unlock().init_modules()

        return unload()

    async def all_ready(self) -> None:
        for broker in self.__brokers:
            await broker.all_ready()

    def add_logger(self, logger: Logger) -> Self:
        self.__loggers.append(logger)
        return self

    def add_listener(self, listener: EventListener) -> Self:
        self.__channel.add_listener(listener)
        return self

    def remove_listener(self, listener: EventListener) -> Self:
        self.__channel.remove_listener(listener)
        return self

    def on_event(self, event: Event, /) -> ContextManager[None]:
        self_event = ModuleEventProxy(self, event)
        return self.dispatch(self_event)

    @contextmanager
    def dispatch(self, event: Event) -> Iterator[None]:
        self.__check_locking()

        with self.__channel.dispatch(event):
            try:
                yield
            finally:
                self.__debug(event)

    def __debug(self, message: object) -> None:
        for logger in self.__loggers:
            logger.debug(message)

    def __check_locking(self) -> None:
        if self.is_locked:
            raise ModuleLockError(f"`{self}` is locked.")

    def __move_module(self, module: Module, priority: Priority) -> None:
        last = priority != Priority.HIGH

        try:
            self.__modules.move_to_end(module, last=last)
        except KeyError as exc:
            raise ModuleNotUsedError(
                f"`{module}` can't be found in the modules used by `{self}`."
            ) from exc

    @classmethod
    def from_name(cls, name: str) -> Module:
        with suppress(KeyError):
            return cls.__instances[name]

        instance = cls(name)
        cls.__instances[name] = instance
        return instance

    @classmethod
    def default(cls) -> Module:
        return cls.from_name("__default__")


def mod(name: str | None = None, /) -> Module:
    if name is None:
        return Module.default()

    return Module.from_name(name)


"""
InjectedFunction
"""


@dataclass(repr=False, frozen=True, slots=True)
class Dependencies:
    lazy_mapping: Lazy[Mapping[str, Injectable[Any]]]

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for name, injectable in self.items():
            with suppress(SkipInjectable):
                yield name, injectable.get_instance()

    async def __aiter__(self) -> AsyncIterator[tuple[str, Any]]:
        for name, injectable in self.items():
            with suppress(SkipInjectable):
                yield name, await injectable.aget_instance()

    @property
    def are_resolved(self) -> bool:
        return self.lazy_mapping.is_set

    async def aget_arguments(self) -> dict[str, Any]:
        return {key: value async for key, value in self}

    def get_arguments(self) -> dict[str, Any]:
        return dict(self)

    def items(self) -> Iterator[tuple[str, Injectable[Any]]]:
        return iter((~self.lazy_mapping).items())

    @classmethod
    def from_iterable(cls, iterable: Iterable[tuple[str, Injectable[Any]]]) -> Self:
        lazy_mapping = Lazy(lambda: dict(iterable))
        return cls(lazy_mapping)

    @classmethod
    def empty(cls) -> Self:
        return cls.from_iterable(())

    @classmethod
    def resolve(
        cls,
        signature: Signature,
        module: Module,
        owner: type | None = None,
    ) -> Self:
        iterable = cls.__resolver(signature, module, owner)
        return cls.from_iterable(iterable)

    @classmethod
    def __resolver(
        cls,
        signature: Signature,
        module: Module,
        owner: type | None = None,
    ) -> Iterator[tuple[str, Injectable[Any]]]:
        for name, annotation in cls.__get_annotations(signature, owner):
            try:
                injectable: Injectable[Any] = module[annotation]
            except KeyError:
                continue

            yield name, injectable

    @staticmethod
    def __get_annotations(
        signature: Signature,
        owner: type | None = None,
    ) -> Iterator[tuple[str, type | Any]]:
        parameters = iter(signature.parameters.items())

        if owner:
            name, _ = next(parameters)
            yield name, owner

        for name, parameter in parameters:
            yield name, parameter.annotation


class Arguments(NamedTuple):
    args: Iterable[Any]
    kwargs: Mapping[str, Any]


class InjectMetadata[**P, T](Caller[P, T], EventListener):
    __slots__ = (
        "__dependencies",
        "__lock",
        "__owner",
        "__signature",
        "__tasks",
        "__wrapped",
    )

    __dependencies: Dependencies
    __lock: ContextManager[Any]
    __owner: type | None
    __signature: Signature
    __tasks: deque[Callable[..., Any]]
    __wrapped: Callable[P, T]

    def __init__(self, wrapped: Callable[P, T], /, threadsafe: bool) -> None:
        self.__dependencies = Dependencies.empty()
        self.__lock = threading.Lock() if threadsafe else nullcontext()
        self.__owner = None
        self.__tasks = deque()
        self.__wrapped = wrapped

    @property
    def signature(self) -> Signature:
        with suppress(AttributeError):
            return self.__signature

        signature = inspect_signature(self.wrapped, eval_str=True)
        self.__signature = signature
        return signature

    @property
    def wrapped(self) -> Callable[P, T]:
        return self.__wrapped

    async def abind(
        self,
        args: Iterable[Any] = (),
        kwargs: Mapping[str, Any] | None = None,
    ) -> Arguments:
        additional_arguments = await self.__dependencies.aget_arguments()
        return self.__bind(args, kwargs, additional_arguments)

    def bind(
        self,
        args: Iterable[Any] = (),
        kwargs: Mapping[str, Any] | None = None,
    ) -> Arguments:
        additional_arguments = self.__dependencies.get_arguments()
        return self.__bind(args, kwargs, additional_arguments)

    async def acall(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        with self.__lock:
            self.__run_tasks()
            arguments = await self.abind(args, kwargs)

        return self.wrapped(*arguments.args, **arguments.kwargs)

    def call(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        with self.__lock:
            self.__run_tasks()
            arguments = self.bind(args, kwargs)

        return self.wrapped(*arguments.args, **arguments.kwargs)

    def set_owner(self, owner: type) -> Self:
        if self.__dependencies.are_resolved:
            raise TypeError(
                "Function owner must be assigned before dependencies are resolved."
            )

        if self.__owner:
            raise TypeError("Function owner is already defined.")

        self.__owner = owner
        return self

    def update(self, module: Module) -> Self:
        self.__dependencies = Dependencies.resolve(self.signature, module, self.__owner)
        return self

    def task[**_P, _T](self, wrapped: Callable[_P, _T] | None = None, /) -> Any:
        def decorator(wp: Callable[_P, _T]) -> Callable[_P, _T]:
            self.__tasks.append(wp)
            return wp

        return decorator(wrapped) if wrapped else decorator

    @singledispatchmethod
    def on_event(self, event: Event, /) -> ContextManager[None] | None:  # type: ignore[override]
        return None

    @on_event.register
    @contextmanager
    def _(self, event: ModuleEvent, /) -> Iterator[None]:
        yield
        self.update(event.module)

    def __bind(
        self,
        args: Iterable[Any],
        kwargs: Mapping[str, Any] | None,
        additional_arguments: dict[str, Any] | None,
    ) -> Arguments:
        if kwargs is None:
            kwargs = {}

        if not additional_arguments:
            return Arguments(args, kwargs)

        bound = self.signature.bind_partial(*args, **kwargs)
        bound.arguments = bound.arguments | additional_arguments | bound.arguments
        return Arguments(bound.args, bound.kwargs)

    def __run_tasks(self) -> None:
        while tasks := self.__tasks:
            task = tasks.popleft()
            task()


class InjectedFunction[**P, T](ABC):
    __slots__ = ("__dict__", "__inject_metadata__")

    __inject_metadata__: InjectMetadata[P, T]

    def __init__(self, metadata: InjectMetadata[P, T]) -> None:
        update_wrapper(self, metadata.wrapped)
        self.__inject_metadata__ = metadata

    def __repr__(self) -> str:  # pragma: no cover
        return repr(self.__inject_metadata__.wrapped)

    def __str__(self) -> str:  # pragma: no cover
        return str(self.__inject_metadata__.wrapped)

    @abstractmethod
    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError

    def __get__(
        self,
        instance: object | None = None,
        owner: type | None = None,
    ) -> Self | MethodType:
        if instance is None:
            return self

        return MethodType(self, instance)

    def __set_name__(self, owner: type, name: str) -> None:
        self.__inject_metadata__.set_owner(owner)


class AsyncInjectedFunction[**P, T](InjectedFunction[P, Awaitable[T]]):
    __slots__ = ()

    def __init__(self, metadata: InjectMetadata[P, Awaitable[T]]) -> None:
        super().__init__(metadata)
        markcoroutinefunction(self)

    async def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return await (await self.__inject_metadata__.acall(*args, **kwargs))


class SyncInjectedFunction[**P, T](InjectedFunction[P, T]):
    __slots__ = ()

    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.__inject_metadata__.call(*args, **kwargs)


def extract_caller[**P, T](
    function: Callable[P, T] | Callable[P, Awaitable[T]],
) -> Caller[P, T]:
    if iscoroutinefunction(function):
        return AsyncCaller(function)

    elif isinstance(function, InjectedFunction):
        return function.__inject_metadata__

    return SyncCaller(function)  # type: ignore[arg-type]
