from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections import OrderedDict
from collections.abc import (
    Callable,
    Collection,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
)
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from enum import StrEnum
from functools import partialmethod, singledispatchmethod, update_wrapper
from inspect import Signature, isclass
from logging import Logger, getLogger
from queue import Empty, Queue
from types import MethodType
from typing import (
    Any,
    ClassVar,
    ContextManager,
    Literal,
    NamedTuple,
    NoReturn,
    Protocol,
    Self,
    override,
    runtime_checkable,
)
from uuid import uuid4

from injection._core.common.event import Event, EventChannel, EventListener
from injection._core.common.invertible import Invertible, SimpleInvertible
from injection._core.common.lazy import Lazy, LazyMapping
from injection._core.common.threading import synchronized
from injection._core.common.type import InputType, TypeInfo, get_return_types
from injection._core.hook import Hook, apply_hooks
from injection.exceptions import (
    InjectionError,
    ModuleError,
    ModuleLockError,
    ModuleNotUsedError,
    NoInjectable,
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

    @override
    def __str__(self) -> str:
        length = len(self.classes)
        formatted_types = ", ".join(f"`{cls}`" for cls in self.classes)
        return (
            f"{length} dependenc{"ies" if length > 1 else "y"} have been "
            f"updated{f": {formatted_types}" if formatted_types else ""}."
        )


@dataclass(frozen=True, slots=True)
class ModuleEvent(Event, ABC):
    module: Module


@dataclass(frozen=True, slots=True)
class ModuleEventProxy(ModuleEvent):
    event: Event

    @override
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

    @override
    def __str__(self) -> str:
        return f"`{self.module}` now uses `{self.module_added}`."


@dataclass(frozen=True, slots=True)
class ModuleRemoved(ModuleEvent):
    module_removed: Module

    @override
    def __str__(self) -> str:
        return f"`{self.module}` no longer uses `{self.module_removed}`."


@dataclass(frozen=True, slots=True)
class ModulePriorityUpdated(ModuleEvent):
    module_updated: Module
    priority: Priority

    @override
    def __str__(self) -> str:
        return (
            f"In `{self.module}`, the priority `{self.priority}` "
            f"has been applied to `{self.module_updated}`."
        )


"""
Injectables
"""


@runtime_checkable
class Injectable[T](Protocol):
    __slots__ = ()

    @property
    def is_locked(self) -> bool:
        return False

    def unlock(self) -> None:
        return

    @abstractmethod
    def get_instance(self) -> T:
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class BaseInjectable[T](Injectable[T], ABC):
    factory: Callable[..., T]


class SimpleInjectable[T](BaseInjectable[T]):
    __slots__ = ()

    @override
    def get_instance(self) -> T:
        return self.factory()


class SingletonInjectable[T](BaseInjectable[T]):
    __slots__ = ("__dict__",)

    __key: ClassVar[str] = "$instance"

    @property
    def cache(self) -> MutableMapping[str, Any]:
        return self.__dict__

    @property
    @override
    def is_locked(self) -> bool:
        return self.__key in self.cache

    @override
    def unlock(self) -> None:
        self.cache.clear()

    @override
    def get_instance(self) -> T:
        with suppress(KeyError):
            return self.cache[self.__key]

        with synchronized():
            instance = self.factory()
            self.cache[self.__key] = instance

        return instance


@dataclass(repr=False, frozen=True, slots=True)
class ShouldBeInjectable[T](Injectable[T]):
    cls: type[T]

    @override
    def get_instance(self) -> NoReturn:
        raise InjectionError(f"`{self.cls}` should be an injectable.")

    @classmethod
    def from_callable(cls, callable: Callable[..., T]) -> Self:
        if not isclass(callable):
            raise TypeError(f"`{callable}` should be a class.")

        return cls(callable)


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

type InjectableFactory[T] = Callable[[Callable[..., T]], Injectable[T]]


class Record[T](NamedTuple):
    injectable: Injectable[T]
    mode: Mode


@dataclass(repr=False, eq=False, kw_only=True, slots=True)
class Updater[T]:
    factory: Callable[..., T]
    classes: Iterable[InputType[T]]
    injectable_factory: InjectableFactory[T]
    mode: Mode

    def make_record(self) -> Record[T]:
        injectable = self.injectable_factory(self.factory)
        return Record(injectable, self.mode)


class LocatorHooks[T](NamedTuple):
    on_conflict: Hook[[Record[T], Record[T], InputType[T]], bool]
    on_input: Hook[[Iterable[InputType[T]]], Iterable[InputType[T]]]
    on_update: Hook[[Updater[T]], Updater[T]]

    @classmethod
    def default(cls) -> Self:
        return cls(
            on_conflict=Hook(),
            on_input=Hook(),
            on_update=Hook(),
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

    static_hooks: ClassVar[LocatorHooks[Any]] = LocatorHooks.default()

    @override
    def __getitem__[T](self, cls: InputType[T], /) -> Injectable[T]:
        for input_class in self.__standardize_inputs((cls,)):
            try:
                record = self.__records[input_class]
            except KeyError:
                continue

            return record.injectable

        raise NoInjectable(cls)

    @override
    def __contains__(self, cls: InputType[Any], /) -> bool:
        return any(
            input_class in self.__records
            for input_class in self.__standardize_inputs((cls,))
        )

    @property
    @override
    def is_locked(self) -> bool:
        return any(injectable.is_locked for injectable in self.__injectables)

    @property
    def __injectables(self) -> frozenset[Injectable[Any]]:
        return frozenset(record.injectable for record in self.__records.values())

    @synchronized()
    def update[T](self, updater: Updater[T]) -> Self:
        updater = self.__update_preprocessing(updater)
        record = updater.make_record()
        records = dict(self.__prepare_for_updating(updater.classes, record))

        if records:
            event = LocatorDependenciesUpdated(self, records.keys(), record.mode)

            with self.dispatch(event):
                self.__records.update(records)

        return self

    @override
    @synchronized()
    def unlock(self) -> Self:
        for injectable in self.__injectables:
            injectable.unlock()

        return self

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

    def __keep_new_record[T](
        self,
        new: Record[T],
        existing: Record[T],
        cls: InputType[T],
    ) -> bool:
        return apply_hooks(
            lambda *args, **kwargs: False,
            self.static_hooks.on_conflict,
        )(new, existing, cls)

    def __standardize_inputs[T](
        self,
        classes: Iterable[InputType[T]],
    ) -> Iterable[InputType[T]]:
        return apply_hooks(lambda c: c, self.static_hooks.on_input)(classes)

    def __update_preprocessing[T](self, updater: Updater[T]) -> Updater[T]:
        return apply_hooks(lambda u: u, self.static_hooks.on_update)(updater)


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


@dataclass(eq=False, frozen=True, slots=True)
class Module(Broker, EventListener):
    name: str = field(default_factory=lambda: f"anonymous@{uuid4().hex[:7]}")
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

    @override
    def __getitem__[T](self, cls: InputType[T], /) -> Injectable[T]:
        for broker in self.__brokers:
            with suppress(KeyError):
                return broker[cls]

        raise NoInjectable(cls)

    @override
    def __contains__(self, cls: InputType[Any], /) -> bool:
        return any(cls in broker for broker in self.__brokers)

    @property
    @override
    def is_locked(self) -> bool:
        return any(broker.is_locked for broker in self.__brokers)

    @property
    def __brokers(self) -> Iterator[Broker]:
        yield from tuple(self.__modules)
        yield self.__locator

    def injectable[**P, T](  # type: ignore[no-untyped-def]
        self,
        wrapped: Callable[P, T] | None = None,
        /,
        *,
        cls: InjectableFactory[T] = SimpleInjectable,
        inject: bool = True,
        on: TypeInfo[T] = (),
        mode: Mode | ModeStr = Mode.get_default(),
    ):
        def decorator(wp):  # type: ignore[no-untyped-def]
            factory = self.inject(wp, return_factory=True) if inject else wp
            classes = get_return_types(wp, on)
            updater = Updater(
                factory=factory,
                classes=classes,
                injectable_factory=cls,
                mode=Mode(mode),
            )
            self.update(updater)
            return wp

        return decorator(wrapped) if wrapped else decorator

    singleton = partialmethod(injectable, cls=SingletonInjectable)

    def should_be_injectable[T](self, wrapped: type[T] | None = None, /):  # type: ignore[no-untyped-def]
        def decorator(wp):  # type: ignore[no-untyped-def]
            updater = Updater(
                factory=wp,
                classes=(wp,),
                injectable_factory=ShouldBeInjectable.from_callable,
                mode=Mode.FALLBACK,
            )
            self.update(updater)
            return wp

        return decorator(wrapped) if wrapped else decorator

    def constant[**P, T](  # type: ignore[no-untyped-def]
        self,
        wrapped: Callable[P, T] | None = None,
        /,
        *,
        on: TypeInfo[T] = (),
        mode: Mode | ModeStr = Mode.get_default(),
    ):
        def decorator(wp):  # type: ignore[no-untyped-def]
            instance = wp()
            self.set_constant(
                instance,
                on=on,
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
        if not alias:
            cls = type(instance)
            on = (cls, on)

        self.injectable(
            lambda: instance,
            inject=False,
            on=on,
            mode=mode,
        )
        return self

    def inject[**P, T](  # type: ignore[no-untyped-def]
        self,
        wrapped: Callable[P, T] | None = None,
        /,
        *,
        return_factory: bool = False,
    ):
        def decorator(wp):  # type: ignore[no-untyped-def]
            if not return_factory and isclass(wp):
                wp.__init__ = self.inject(wp.__init__)
                return wp

            function = InjectedFunction(wp)

            @function.on_setup
            def listen() -> None:
                function.update(self)
                self.add_listener(function)

            return function

        return decorator(wrapped) if wrapped else decorator

    def find_instance[T](self, cls: InputType[T]) -> T:
        injectable = self[cls]
        return injectable.get_instance()

    def get_instance[T](self, cls: InputType[T]) -> T | None:
        try:
            return self.find_instance(cls)
        except KeyError:
            return None

    def get_lazy_instance[T](
        self,
        cls: InputType[T],
        *,
        cache: bool = False,
    ) -> Invertible[T | None]:
        if cache:
            return Lazy(lambda: self.get_instance(cls))

        function = self.inject(lambda instance=None: instance)
        function.set_owner(cls)
        return SimpleInvertible(function)

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
    ) -> Iterator[None]:
        self.use(module, priority=priority)
        yield
        self.stop_using(module)

    def change_priority(self, module: Module, priority: Priority | PriorityStr) -> Self:
        priority = Priority(priority)
        event = ModulePriorityUpdated(self, module, priority)

        with self.dispatch(event):
            self.__move_module(module, priority)

        return self

    @override
    @synchronized()
    def unlock(self) -> Self:
        for broker in self.__brokers:
            broker.unlock()

        return self

    def add_logger(self, logger: Logger) -> Self:
        self.__loggers.append(logger)
        return self

    def add_listener(self, listener: EventListener) -> Self:
        self.__channel.add_listener(listener)
        return self

    def remove_listener(self, listener: EventListener) -> Self:
        self.__channel.remove_listener(listener)
        return self

    @override
    def on_event(self, event: Event, /) -> ContextManager[None] | None:
        self_event = ModuleEventProxy(self, event)
        return self.dispatch(self_event)

    @contextmanager
    def dispatch(self, event: Event) -> Iterator[None]:
        self.__check_locking()

        with self.__channel.dispatch(event):
            yield
            message = str(event)
            self.__debug(message)

    def __debug(self, message: object) -> None:
        for logger in tuple(self.__loggers):
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

        with synchronized():
            instance = cls(name)
            cls.__instances[name] = instance

        return instance

    @classmethod
    def default(cls) -> Module:
        return cls.from_name("__default__")


"""
InjectedFunction
"""


@dataclass(repr=False, frozen=True, slots=True)
class Dependencies:
    mapping: Mapping[str, Injectable[Any]]

    def __bool__(self) -> bool:
        return bool(self.mapping)

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for name, injectable in self.mapping.items():
            yield name, injectable.get_instance()

    @property
    def are_resolved(self) -> bool:
        if isinstance(self.mapping, LazyMapping) and not self.mapping.is_set:
            return False

        return bool(self)

    @property
    def arguments(self) -> OrderedDict[str, Any]:
        return OrderedDict(self)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Injectable[Any]]) -> Self:
        return cls(mapping)

    @classmethod
    def empty(cls) -> Self:
        return cls.from_mapping({})

    @classmethod
    def resolve(
        cls,
        signature: Signature,
        module: Module,
        owner: type | None = None,
    ) -> Self:
        dependencies = LazyMapping(cls.__resolver(signature, module, owner))
        return cls.from_mapping(dependencies)

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


class InjectedFunction[**P, T](EventListener):
    __slots__ = (
        "__dict__",
        "__wrapped__",
        "__dependencies",
        "__owner",
        "__setup_queue",
    )

    __signature__: Signature
    __wrapped__: Callable[P, T]
    __dependencies: Dependencies
    __owner: type | None
    __setup_queue: Queue[Callable[..., Any]] | None

    def __init__(self, wrapped: Callable[P, T], /) -> None:
        update_wrapper(self, wrapped, updated=())
        self.__update_vars_from(wrapped)
        self.__dependencies = Dependencies.empty()
        self.__owner = None
        self.__setup_queue = Queue()

    @override
    def __repr__(self) -> str:  # pragma: no cover
        return repr(self.wrapped)

    @override
    def __str__(self) -> str:  # pragma: no cover
        return str(self.wrapped)

    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        self.__setup()
        arguments = self.bind(args, kwargs)
        return self.wrapped(*arguments.args, **arguments.kwargs)

    def __get__(
        self,
        instance: object | None = None,
        owner: type | None = None,
    ) -> Self | MethodType:
        if instance is None:
            return self

        return MethodType(self, instance)

    def __set_name__(self, owner: type, name: str) -> None:
        self.set_owner(owner)

    @property
    def signature(self) -> Signature:
        with suppress(AttributeError):
            return self.__signature__

        with synchronized():
            signature = inspect.signature(self.wrapped, eval_str=True)
            self.__signature__ = signature

        return signature

    @property
    def wrapped(self) -> Callable[P, T]:
        return self.__wrapped__

    def bind(
        self,
        args: Iterable[Any] = (),
        kwargs: Mapping[str, Any] | None = None,
    ) -> Arguments:
        if kwargs is None:
            kwargs = {}

        if not self.__dependencies:
            return Arguments(args, kwargs)

        bound = self.signature.bind_partial(*args, **kwargs)
        bound.arguments = (
            bound.arguments | self.__dependencies.arguments | bound.arguments
        )
        return Arguments(bound.args, bound.kwargs)

    def set_owner(self, owner: type) -> Self:
        if self.__dependencies.are_resolved:
            raise TypeError(
                "Function owner must be assigned before dependencies are resolved."
            )

        if self.__owner:
            raise TypeError("Function owner is already defined.")

        self.__owner = owner
        return self

    @synchronized()
    def update(self, module: Module) -> Self:
        self.__dependencies = Dependencies.resolve(self.signature, module, self.__owner)
        return self

    def on_setup[**_P, _T](self, wrapped: Callable[_P, _T] | None = None, /):  # type: ignore[no-untyped-def]
        def decorator(wp):  # type: ignore[no-untyped-def]
            queue = self.__setup_queue

            if queue is None:
                raise RuntimeError(f"`{self}` is already up.")

            queue.put_nowait(wp)
            return wp

        return decorator(wrapped) if wrapped else decorator

    @singledispatchmethod
    @override
    def on_event(self, event: Event, /) -> ContextManager[None] | None:  # type: ignore[override]
        return None

    @on_event.register
    @contextmanager
    def _(self, event: ModuleEvent, /) -> Iterator[None]:
        yield
        self.update(event.module)

    def __close_setup_queue(self) -> None:
        self.__setup_queue = None

    def __setup(self) -> None:
        queue = self.__setup_queue

        if queue is None:
            return

        while True:
            try:
                task = queue.get_nowait()
            except Empty:
                break

            task()
            queue.task_done()

        queue.join()
        self.__close_setup_queue()

    def __update_vars_from(self, obj: Any) -> None:
        try:
            variables = vars(obj)
        except TypeError:
            ...
        else:
            self.__update_vars(variables)

    def __update_vars(self, variables: Mapping[str, Any]) -> None:
        restricted_vars = frozenset(("__signature__", "__wrapped__")) | frozenset(
            var for var in dir(self) if not self.__is_dunder(var)
        )
        vars(self).update(
            (var, value)
            for var, value in variables.items()
            if var not in restricted_vars
        )

    @staticmethod
    def __is_dunder(var: str) -> bool:
        return var.startswith("__") and var.endswith("__")
