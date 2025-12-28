from __future__ import annotations

import itertools
from abc import ABC
from collections import OrderedDict, deque
from collections.abc import (
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Collection,
    Container,
    Generator,
    Iterable,
    Iterator,
    Mapping,
)
from contextlib import asynccontextmanager, contextmanager, suppress
from dataclasses import dataclass, field
from enum import StrEnum
from functools import partialmethod, singledispatchmethod, update_wrapper
from inspect import (
    BoundArguments,
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
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    ClassVar,
    ContextManager,
    Literal,
    NamedTuple,
    Self,
    overload,
)

from type_analyzer import MatchingTypesConfig, iter_matching_types, matching_types

from injection._core.common.asynchronous import (
    Caller,
    HiddenCaller,
    SimpleAwaitable,
)
from injection._core.common.event import Event, EventChannel, EventListener
from injection._core.common.invertible import Invertible, SimpleInvertible
from injection._core.common.key import new_short_key
from injection._core.common.lazy import Lazy
from injection._core.common.threading import get_lock
from injection._core.common.type import (
    InputType,
    TypeInfo,
    get_yield_hints,
    iter_return_types,
)
from injection._core.injectables import (
    AsyncCMScopedInjectable,
    CMScopedInjectable,
    ConstantInjectable,
    Injectable,
    ScopedInjectable,
    ScopedSlotInjectable,
    ShouldBeInjectable,
    SimpleScopedInjectable,
    SingletonInjectable,
    TransientInjectable,
)
from injection._core.locator import (
    DynamicInjectableBroker,
    InjectableBroker,
    InjectableFactory,
    InjectionProvider,
    Locator,
    Mode,
    ModeStr,
    Recipe,
    StaticInjectableBroker,
    Updater,
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
class ModuleEvent(Event, ABC):
    module: Module


@dataclass(frozen=True, slots=True)
class ModuleEventProxy(ModuleEvent):
    event: Event

    def __str__(self) -> str:
        return f"`{self.module}` has propagated an event: {self.origin}"

    @property
    def origin(self) -> Event:
        reversed_proxy_history = reversed(tuple(self.proxy_history))
        return next(reversed_proxy_history, self).event

    @property
    def proxy_history(self) -> Iterator[ModuleEventProxy]:
        event = self.event

        if isinstance(event, ModuleEventProxy):
            yield event
            yield from event.proxy_history


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
Module
"""


class Priority(StrEnum):
    LOW = "low"
    HIGH = "high"

    @classmethod
    def get_default(cls) -> Priority:
        return cls.LOW


type PriorityStr = Literal["low", "high"]

type ContextManagerRecipe[**P, T] = (
    Callable[P, ContextManager[T]] | Callable[P, AsyncContextManager[T]]
)
type GeneratorRecipe[**P, T] = (
    Callable[P, Generator[T, Any, Any]] | Callable[P, AsyncGenerator[T, Any]]
)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _ScopedContext[**P, T]:
    cls: type[ScopedInjectable[Any, T]]
    hints: Collection[TypeInfo[T]]
    wrapper: Recipe[P, T] | ContextManagerRecipe[P, T]


@dataclass(eq=False, frozen=True, slots=True)
class Module(EventListener, InjectionProvider):  # type: ignore[misc]
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
        key_types = self.__matching_key_types(cls)

        for locator in self._iter_locators():
            for key_type in key_types:
                with suppress(KeyError):
                    return locator.request(key_type, self)

        raise NoInjectable(cls)

    def __contains__(self, cls: InputType[Any], /) -> bool:
        key_types = self.__matching_key_types(cls)
        return any(
            key_type in locator
            for locator in self._iter_locators()
            for key_type in key_types
        )

    @property
    def is_locked(self) -> bool:
        return any(locator.is_locked(self) for locator in self._iter_locators())

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
            hints = on if ignore_type_hint else (wp, on)
            broker = (
                DynamicInjectableBroker(cls, wp)
                if inject
                else StaticInjectableBroker.from_factory(cls, wp)
            )
            self.update_from(hints, broker, mode)
            return wp

        return decorator(wrapped) if wrapped else decorator

    singleton = partialmethod(injectable, cls=SingletonInjectable)
    constant = partialmethod(injectable, cls=SingletonInjectable, inject=False)

    def scoped[**P, T](
        self,
        scope_name: str,
        /,
        *,
        ignore_type_hint: bool = False,
        inject: bool = True,
        on: TypeInfo[T] = (),
        mode: Mode | ModeStr = Mode.get_default(),
    ) -> Any:
        def decorator(
            wrapped: Recipe[P, T] | GeneratorRecipe[P, T],
        ) -> Recipe[P, T] | GeneratorRecipe[P, T]:
            if isasyncgenfunction(wrapped):
                ctx = _ScopedContext(
                    cls=AsyncCMScopedInjectable,
                    hints=() if ignore_type_hint else get_yield_hints(wrapped),
                    wrapper=asynccontextmanager(wrapped),
                )

            elif isgeneratorfunction(wrapped):
                ctx = _ScopedContext(
                    cls=CMScopedInjectable,
                    hints=() if ignore_type_hint else get_yield_hints(wrapped),
                    wrapper=contextmanager(wrapped),
                )

            else:
                ctx = _ScopedContext(
                    cls=SimpleScopedInjectable,
                    hints=() if ignore_type_hint else (wrapped,),
                    wrapper=wrapped,
                )

            self.injectable(
                ctx.wrapper,
                cls=ctx.cls.bind_scope_name(scope_name),
                ignore_type_hint=True,
                inject=inject,
                on=(*ctx.hints, on),
                mode=mode,
            )
            return wrapped

        return decorator

    def should_be_injectable[T](self, wrapped: type[T] | None = None, /) -> Any:
        def decorator(wp: type[T]) -> type[T]:
            broker = StaticInjectableBroker(ShouldBeInjectable(wp))
            self.update_from(wp, broker, Mode.FALLBACK)
            return wp

        return decorator(wrapped) if wrapped else decorator

    def set_constant[T](
        self,
        instance: T,
        on: TypeInfo[T] = (),
        *,
        alias: bool = False,
        mode: Mode | ModeStr = Mode.get_default(),
    ) -> T:
        if not alias:
            on = (type(instance), on)

        elif not on:
            raise ValueError("`on` must be provided when `alias` is `True`.")

        broker = StaticInjectableBroker(ConstantInjectable(instance))
        self.update_from(on, broker, mode)
        return instance

    def reserve_scoped_slot[T](
        self,
        cls: InputType[T],
        /,
        scope_name: str,
        *,
        mode: Mode | ModeStr = Mode.get_default(),
    ) -> SlotKey[T]:
        injectable = ScopedSlotInjectable(cls, scope_name)
        broker = StaticInjectableBroker(injectable)
        self.update_from(cls, broker, mode)
        return injectable.key

    def inject[**P, T](
        self,
        wrapped: Callable[P, T] | None = None,
        /,
        *,
        threadsafe: bool | None = None,
    ) -> Any:
        def decorator(wp: Callable[P, T]) -> Callable[P, T]:
            if isclass(wp):
                wp.__init__ = self.inject(wp.__init__, threadsafe=threadsafe)
                return wp

            return self.make_injected_function(wp, threadsafe)

        return decorator(wrapped) if wrapped else decorator

    def create_metadata[**P, T](
        self,
        wrapped: Callable[P, T],
        /,
        threadsafe: bool | None = None,
    ) -> InjectMetadata[P, T]:
        return InjectMetadata(wrapped, threadsafe).listen(self)

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def make_injected_function[**P, T](
            self,
            wrapped: Callable[P, T],
            /,
            threadsafe: bool | None = ...,
        ) -> SyncInjectedFunction[P, T]: ...

        @overload
        def make_injected_function[**P, T](
            self,
            wrapped: Callable[P, Awaitable[T]],
            /,
            threadsafe: bool | None = ...,
        ) -> AsyncInjectedFunction[P, T]: ...

    def make_injected_function[**P, T](
        self,
        wrapped: Callable[P, T],
        /,
        threadsafe: bool | None = None,
    ) -> InjectedFunction[P, T]:
        metadata = self.create_metadata(wrapped, threadsafe)

        if iscoroutinefunction(wrapped):
            return AsyncInjectedFunction(metadata)  # type: ignore[arg-type, return-value]

        return SyncInjectedFunction(metadata)

    def make_async_factory[T](
        self,
        wrapped: type[T],
        /,
        threadsafe: bool | None = None,
    ) -> Callable[..., Awaitable[T]]:
        return self.create_metadata(wrapped, threadsafe).acall

    async def afind_instance[T](
        self,
        cls: InputType[T],
        *,
        threadsafe: bool | None = None,
    ) -> T:
        with get_lock(threadsafe):
            injectable = self[cls]
            return await injectable.aget_instance()

    def find_instance[T](
        self,
        cls: InputType[T],
        *,
        threadsafe: bool | None = None,
    ) -> T:
        with get_lock(threadsafe):
            injectable = self[cls]
            return injectable.get_instance()

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        async def aget_instance[T, Default](
            self,
            cls: InputType[T],
            default: Default,
            *,
            threadsafe: bool | None = ...,
        ) -> T | Default: ...

        @overload
        async def aget_instance[T](
            self,
            cls: InputType[T],
            default: T = ...,
            *,
            threadsafe: bool | None = ...,
        ) -> T: ...

    async def aget_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default = NotImplemented,
        *,
        threadsafe: bool | None = None,
    ) -> T | Default:
        try:
            return await self.afind_instance(cls, threadsafe=threadsafe)
        except (KeyError, SkipInjectable):
            return default

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def get_instance[T, Default](
            self,
            cls: InputType[T],
            default: Default,
            *,
            threadsafe: bool | None = ...,
        ) -> T | Default: ...

        @overload
        def get_instance[T](
            self,
            cls: InputType[T],
            default: T = ...,
            *,
            threadsafe: bool | None = ...,
        ) -> T: ...

    def get_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default = NotImplemented,
        *,
        threadsafe: bool | None = None,
    ) -> T | Default:
        try:
            return self.find_instance(cls, threadsafe=threadsafe)
        except (KeyError, SkipInjectable):
            return default

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def aget_lazy_instance[T, Default](
            self,
            cls: InputType[T],
            default: Default,
            *,
            threadsafe: bool | None = ...,
        ) -> Awaitable[T | Default]: ...

        @overload
        def aget_lazy_instance[T](
            self,
            cls: InputType[T],
            default: T = ...,
            *,
            threadsafe: bool | None = ...,
        ) -> Awaitable[T]: ...

    def aget_lazy_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default = NotImplemented,
        *,
        threadsafe: bool | None = None,
    ) -> Awaitable[T | Default]:
        return SimpleAwaitable(
            self.create_metadata(
                lambda instance=default: instance,
                threadsafe=threadsafe,
            )
            .set_owner(cls)  # type: ignore[arg-type]
            .acall
        )

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def get_lazy_instance[T, Default](
            self,
            cls: InputType[T],
            default: Default,
            *,
            threadsafe: bool | None = ...,
        ) -> Invertible[T | Default]: ...

        @overload
        def get_lazy_instance[T](
            self,
            cls: InputType[T],
            default: T = ...,
            *,
            threadsafe: bool | None = ...,
        ) -> Invertible[T]: ...

    def get_lazy_instance[T, Default](
        self,
        cls: InputType[T],
        default: Default = NotImplemented,
        *,
        threadsafe: bool | None = None,
    ) -> Invertible[T | Default]:
        return SimpleInvertible(
            self.create_metadata(
                lambda instance=default: instance,
                threadsafe=threadsafe,
            )
            .set_owner(cls)  # type: ignore[arg-type]
            .call
        )

    def update[T](self, updater: Updater[T]) -> Self:
        self.__locator.update(updater)
        return self

    def update_from[T](
        self,
        on: TypeInfo[T],
        /,
        broker: InjectableBroker[T],
        mode: Mode | ModeStr,
    ) -> Self:
        updater = Updater(
            classes=self.__build_key_types(on),
            broker=broker,
            mode=Mode(mode),
        )
        self.update(updater)
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
        unlock: bool = False,
    ) -> Iterator[Self]:
        self.use(module, priority=priority)

        try:
            yield self
        finally:
            if unlock:
                self.unlock()

            self.stop_using(module)

    def change_priority(self, module: Module, priority: Priority | PriorityStr) -> Self:
        priority = Priority(priority)
        event = ModulePriorityUpdated(self, module, priority)

        with self.dispatch(event):
            self.__move_module(module, priority)

        return self

    def unlock(self) -> Self:
        for locator in self._iter_locators():
            locator.unlock(self)

        return self

    async def all_ready(self) -> None:
        for locator in self._iter_locators():
            await locator.all_ready(self)

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

    def _iter_locators(self) -> Iterator[Locator]:
        for module in self.__modules:
            yield from module._iter_locators()

        yield self.__locator

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

    @staticmethod
    def __build_key_types(input_cls: Any) -> frozenset[Any]:
        config = MatchingTypesConfig(ignore_none=True)
        return frozenset(
            itertools.chain.from_iterable(
                iter_matching_types(cls, config) for cls in iter_return_types(input_cls)
            )
        )

    @staticmethod
    def __matching_key_types(input_cls: Any) -> tuple[Any, ...]:
        config = MatchingTypesConfig(with_origin=True, with_type_alias_value=True)
        return matching_types(input_cls, config)


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

    def iter(self, exclude: Container[str]) -> Iterator[tuple[str, Any]]:
        for name, injectable in self.items(exclude):
            with suppress(SkipInjectable):
                yield name, injectable.get_instance()

    async def aiter(self, exclude: Container[str]) -> AsyncIterator[tuple[str, Any]]:
        for name, injectable in self.items(exclude):
            with suppress(SkipInjectable):
                yield name, await injectable.aget_instance()

    @property
    def are_resolved(self) -> bool:
        return self.lazy_mapping.is_set

    async def aget_arguments(self, *, exclude: Container[str]) -> dict[str, Any]:
        return {key: value async for key, value in self.aiter(exclude)}

    def get_arguments(self, *, exclude: Container[str]) -> dict[str, Any]:
        return dict(self.iter(exclude))

    def items(self, exclude: Container[str]) -> Iterator[tuple[str, Injectable[Any]]]:
        return (
            (name, injectable)
            for name, injectable in (~self.lazy_mapping).items()
            if name not in exclude
        )

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

    def __init__(
        self,
        wrapped: Callable[P, T],
        /,
        threadsafe: bool | None = None,
    ) -> None:
        self.__dependencies = Dependencies.empty()
        self.__lock = get_lock(threadsafe)
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

    async def abind(self, args: Iterable[Any], kwargs: Mapping[str, Any]) -> Arguments:
        arguments = self.__get_arguments(args, kwargs)
        if dependencies := await self.__dependencies.aget_arguments(exclude=arguments):
            return self.__merge_arguments(arguments, dependencies)

        return Arguments(args, kwargs)

    def bind(self, args: Iterable[Any], kwargs: Mapping[str, Any]) -> Arguments:
        arguments = self.__get_arguments(args, kwargs)
        if dependencies := self.__dependencies.get_arguments(exclude=arguments):
            return self.__merge_arguments(arguments, dependencies)

        return Arguments(args, kwargs)

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

    def listen(self, module: Module) -> Self:
        @self.task
        def start_listening() -> None:
            self.update(module)
            module.add_listener(self)

        return self

    @singledispatchmethod
    def on_event(self, event: Event, /) -> ContextManager[None] | None:
        return None

    @on_event.register
    @contextmanager
    def _(self, event: ModuleEvent, /) -> Iterator[None]:
        yield
        self.update(event.module)

    def __get_arguments(
        self,
        args: Iterable[Any],
        kwargs: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self.signature.bind_partial(*args, **kwargs).arguments

    def __merge_arguments(
        self,
        arguments: dict[str, Any],
        additional_arguments: dict[str, Any],
    ) -> Arguments:
        bound = BoundArguments(self.signature, additional_arguments | arguments)  # type: ignore[arg-type]
        return Arguments(bound.args, bound.kwargs)

    def __run_tasks(self) -> None:
        while tasks := self.__tasks:
            task = tasks.popleft()
            task()


class InjectedFunction[**P, T](HiddenCaller[P, T], ABC):
    __slots__ = ("__dict__", "__injection_metadata__")

    __injection_metadata__: InjectMetadata[P, T]

    def __init__(self, metadata: InjectMetadata[P, T]) -> None:
        update_wrapper(self, metadata.wrapped)
        self.__injection_metadata__ = metadata

    def __repr__(self) -> str:  # pragma: no cover
        return repr(self.__injection_metadata__.wrapped)

    def __str__(self) -> str:  # pragma: no cover
        return str(self.__injection_metadata__.wrapped)

    @property
    def __injection_hidden_caller__(self) -> Caller[P, T]:
        return self.__injection_metadata__

    def __get__(
        self,
        instance: object | None = None,
        owner: type | None = None,
    ) -> Self | MethodType:
        if instance is None:
            return self

        return MethodType(self, instance)

    def __set_name__(self, owner: type, name: str) -> None:
        self.__injection_metadata__.set_owner(owner)


class AsyncInjectedFunction[**P, T](InjectedFunction[P, Awaitable[T]]):
    __slots__ = ()

    def __init__(self, metadata: InjectMetadata[P, Awaitable[T]]) -> None:
        super().__init__(metadata)
        markcoroutinefunction(self)

    async def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return await (await self.__injection_metadata__.acall(*args, **kwargs))


class SyncInjectedFunction[**P, T](InjectedFunction[P, T]):
    __slots__ = ()

    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.__injection_metadata__.call(*args, **kwargs)
