from __future__ import annotations

import inspect
import logging
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
from enum import Enum
from functools import partialmethod, singledispatchmethod, update_wrapper
from inspect import Signature, isclass
from types import MethodType, UnionType
from typing import (
    Any,
    ClassVar,
    ContextManager,
    Literal,
    NamedTuple,
    NoReturn,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from injection.common.event import Event, EventChannel, EventListener
from injection.common.invertible import Invertible, SimpleInvertible
from injection.common.lazy import Lazy, LazyMapping
from injection.common.queue import LimitedQueue
from injection.common.tools.threading import synchronized
from injection.common.tools.type import find_types, format_type, get_origins
from injection.exceptions import (
    InjectionError,
    ModuleError,
    ModuleLockError,
    ModuleNotUsedError,
    NoInjectable,
)

__all__ = ("Injectable", "Mode", "Module", "Priority")

_logger = logging.getLogger(__name__)

_In_T = TypeVar("_In_T", covariant=False)
_Co_T = TypeVar("_Co_T", covariant=True)


"""
Events
"""


@dataclass(frozen=True, slots=True)
class ContainerEvent(Event, ABC):
    on_container: Container


@dataclass(frozen=True, slots=True)
class ContainerDependenciesUpdated(ContainerEvent):
    classes: Collection[type]
    mode: Mode

    def __str__(self) -> str:
        length = len(self.classes)
        formatted_classes = ", ".join(f"`{format_type(cls)}`" for cls in self.classes)
        return (
            f"{length} container dependenc{'ies' if length > 1 else 'y'} have been "
            f"updated{f': {formatted_classes}' if formatted_classes else ''}."
        )


@dataclass(frozen=True, slots=True)
class ModuleEvent(Event, ABC):
    on_module: Module


@dataclass(frozen=True, slots=True)
class ModuleEventProxy(ModuleEvent):
    event: Event

    def __str__(self) -> str:
        return f"`{self.on_module}` has propagated an event: {self.origin}"

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
        return f"`{self.on_module}` now uses `{self.module_added}`."


@dataclass(frozen=True, slots=True)
class ModuleRemoved(ModuleEvent):
    module_removed: Module

    def __str__(self) -> str:
        return f"`{self.on_module}` no longer uses `{self.module_removed}`."


@dataclass(frozen=True, slots=True)
class ModulePriorityUpdated(ModuleEvent):
    module_updated: Module
    priority: Priority

    def __str__(self) -> str:
        return (
            f"In `{self.on_module}`, the priority `{self.priority}` "
            f"has been applied to `{self.module_updated}`."
        )


"""
Injectables
"""


@runtime_checkable
class Injectable(Protocol[_Co_T]):
    __slots__ = ()

    def __init__(self, __factory: Callable[[], _Co_T] = None, /):
        pass

    @property
    def is_locked(self) -> bool:
        return False

    def unlock(self):
        return

    @abstractmethod
    def get_instance(self) -> _Co_T:
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class BaseInjectable(Injectable[_In_T], ABC):
    factory: Callable[[], _In_T]


class NewInjectable(BaseInjectable[_In_T]):
    __slots__ = ()

    def get_instance(self) -> _In_T:
        return self.factory()


class SingletonInjectable(BaseInjectable[_In_T]):
    __slots__ = ("__dict__",)

    __INSTANCE_KEY: ClassVar[str] = "$instance"

    @property
    def cache(self) -> MutableMapping[str, Any]:
        return self.__dict__

    @property
    def is_locked(self) -> bool:
        return self.__INSTANCE_KEY in self.cache

    def unlock(self):
        self.cache.clear()

    def get_instance(self) -> _In_T:
        with suppress(KeyError):
            return self.cache[self.__INSTANCE_KEY]

        with synchronized():
            instance = self.factory()
            self.cache[self.__INSTANCE_KEY] = instance

        return instance


@dataclass(repr=False, frozen=True, slots=True)
class ShouldBeInjectable(Injectable[_In_T]):
    cls: type[_In_T]

    def get_instance(self) -> NoReturn:
        raise InjectionError(f"`{format_type(self.cls)}` should be an injectable.")


"""
Broker
"""


@runtime_checkable
class Broker(Protocol):
    __slots__ = ()

    @abstractmethod
    def __getitem__(self, cls: type[_In_T] | UnionType, /) -> Injectable[_In_T]:
        raise NotImplementedError

    @abstractmethod
    def __contains__(self, cls: type | UnionType, /) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_locked(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def unlock(self):
        raise NotImplementedError


"""
Container
"""


class Mode(str, Enum):
    FALLBACK = "fallback"
    NORMAL = "normal"
    OVERRIDE = "override"

    @property
    def rank(self) -> int:
        return tuple(type(self)).index(self)

    @classmethod
    def get_default(cls):
        return cls.NORMAL


ModeStr = Literal["fallback", "normal", "override"]


class Record(NamedTuple):
    injectable: Injectable
    mode: Mode


@dataclass(repr=False, frozen=True, slots=True)
class Container(Broker):
    __records: dict[type, Record] = field(default_factory=dict, init=False)
    __channel: EventChannel = field(default_factory=EventChannel, init=False)

    def __getitem__(self, cls: type[_In_T] | UnionType, /) -> Injectable[_In_T]:
        for cls in get_origins(cls):
            try:
                injectable, _ = self.__records[cls]
            except KeyError:
                continue

            return injectable

        raise NoInjectable(cls)

    def __contains__(self, cls: type | UnionType, /) -> bool:
        return any(cls in self.__records for cls in get_origins(cls))

    @property
    def is_locked(self) -> bool:
        return any(injectable.is_locked for injectable in self.__injectables)

    @property
    def __injectables(self) -> frozenset[Injectable]:
        return frozenset(injectable for injectable, _ in self.__records.values())

    @synchronized()
    def update(
        self,
        classes: Iterable[type | UnionType],
        injectable: Injectable,
        mode: Mode | ModeStr,
    ):
        mode = Mode(mode)
        records = {
            cls: Record(injectable, mode)
            for cls in self.__classes_to_update(classes, mode)
        }

        if records:
            event = ContainerDependenciesUpdated(self, records.keys(), mode)

            with self.notify(event):
                self.__records.update(records)

        return self

    @synchronized()
    def unlock(self):
        for injectable in self.__injectables:
            injectable.unlock()

        return self

    def add_listener(self, listener: EventListener):
        self.__channel.add_listener(listener)
        return self

    def notify(self, event: Event):
        return self.__channel.dispatch(event)

    def __classes_to_update(
        self,
        classes: Iterable[type | UnionType],
        mode: Mode,
    ) -> Iterator[type]:
        rank = mode.rank

        for cls in frozenset(get_origins(*classes)):
            try:
                _, current_mode = self.__records[cls]

            except KeyError:
                pass

            else:
                if mode == current_mode:
                    raise RuntimeError(
                        f"An injectable already exists for the class `{format_type(cls)}`."
                    )

                elif rank < current_mode.rank:
                    continue

            yield cls


"""
Module
"""


class Priority(str, Enum):
    LOW = "low"
    HIGH = "high"

    @classmethod
    def get_default(cls):
        return cls.LOW


PriorityStr = Literal["low", "high"]


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class Module(EventListener, Broker):
    name: str | None = field(default=None)
    __channel: EventChannel = field(default_factory=EventChannel, init=False)
    __container: Container = field(default_factory=Container, init=False)
    __modules: OrderedDict[Module, None] = field(
        default_factory=OrderedDict,
        init=False,
    )

    def __post_init__(self):
        self.__container.add_listener(self)

    def __getitem__(self, cls: type[_In_T] | UnionType, /) -> Injectable[_In_T]:
        for broker in self.__brokers:
            with suppress(KeyError):
                return broker[cls]

        raise NoInjectable(cls)

    def __setitem__(self, cls: type | UnionType, injectable: Injectable, /):
        self.update((cls,), injectable)

    def __contains__(self, cls: type | UnionType, /) -> bool:
        return any(cls in broker for broker in self.__brokers)

    def __str__(self) -> str:
        return self.name or object.__str__(self)

    @property
    def is_locked(self) -> bool:
        return any(broker.is_locked for broker in self.__brokers)

    @property
    def __brokers(self) -> Iterator[Broker]:
        yield from tuple(self.__modules)
        yield self.__container

    def injectable(
        self,
        wrapped: Callable[..., Any] = None,
        /,
        *,
        cls: type[Injectable] = NewInjectable,
        inject: bool = True,
        on: type | Iterable[type] | UnionType = (),
        mode: Mode | ModeStr = Mode.get_default(),
    ):
        def decorator(wp):
            factory = self.inject(wp, return_factory=True) if inject else wp
            injectable = cls(factory)
            classes = find_types(wp, on)
            self.update(classes, injectable, mode)
            return wp

        return decorator(wrapped) if wrapped else decorator

    singleton = partialmethod(injectable, cls=SingletonInjectable)

    def should_be_injectable(self, wrapped: type = None, /):
        def decorator(wp):
            self.update(
                (wp,),
                ShouldBeInjectable(wp),
                mode=Mode.FALLBACK,
            )
            return wp

        return decorator(wrapped) if wrapped else decorator

    def set_constant(
        self,
        instance: _In_T,
        on: type | Iterable[type] | UnionType = (),
        *,
        mode: Mode | ModeStr = Mode.get_default(),
    ) -> _In_T:
        cls = type(instance)
        self.injectable(
            lambda: instance,
            inject=False,
            on=(cls, on),  # type: ignore
            mode=mode,
        )
        return instance

    def inject(
        self,
        wrapped: Callable[..., Any] = None,
        /,
        *,
        return_factory: bool = False,
    ):
        def decorator(wp):
            if not return_factory and isclass(wp):
                wp.__init__ = self.inject(wp.__init__)
                return wp

            function = InjectedFunction(wp)

            @function.on_setup
            def listen():
                function.update(self)
                self.add_listener(function)

            return function

        return decorator(wrapped) if wrapped else decorator

    def resolve(self, cls: type[_In_T]) -> _In_T:
        injectable = self[cls]
        return injectable.get_instance()

    def get_instance(self, cls: type[_In_T]) -> _In_T | None:
        try:
            return self.resolve(cls)
        except KeyError:
            return None

    def get_lazy_instance(
        self,
        cls: type[_In_T],
        *,
        cache: bool = False,
    ) -> Invertible[_In_T | None]:
        if cache:
            return Lazy(lambda: self.get_instance(cls))

        function = self.inject(lambda instance=None: instance)
        function.set_owner(cls)
        return SimpleInvertible(function)

    def update(
        self,
        classes: Iterable[type | UnionType],
        injectable: Injectable,
        mode: Mode | ModeStr = Mode.get_default(),
    ):
        self.__container.update(classes, injectable, mode)
        return self

    def use(
        self,
        module: Module,
        *,
        priority: Priority | PriorityStr = Priority.get_default(),
    ):
        if module is self:
            raise ModuleError("Module can't be used by itself.")

        if module in self.__modules:
            raise ModuleError(f"`{self}` already uses `{module}`.")

        priority = Priority(priority)
        event = ModuleAdded(self, module, priority)

        with self.notify(event):
            self.__modules[module] = None
            self.__move_module(module, priority)
            module.add_listener(self)

        return self

    def stop_using(self, module: Module):
        event = ModuleRemoved(self, module)

        with suppress(KeyError):
            with self.notify(event):
                self.__modules.pop(module)
                module.remove_listener(self)

        return self

    @contextmanager
    def use_temporarily(
        self,
        module: Module,
        *,
        priority: Priority | PriorityStr = Priority.get_default(),
    ):
        self.use(module, priority=priority)
        yield
        self.stop_using(module)

    def change_priority(self, module: Module, priority: Priority | PriorityStr):
        priority = Priority(priority)
        event = ModulePriorityUpdated(self, module, priority)

        with self.notify(event):
            self.__move_module(module, priority)

        return self

    @synchronized()
    def unlock(self):
        for broker in self.__brokers:
            broker.unlock()

        return self

    def add_listener(self, listener: EventListener):
        self.__channel.add_listener(listener)
        return self

    def remove_listener(self, listener: EventListener):
        self.__channel.remove_listener(listener)
        return self

    def on_event(self, event: Event, /) -> ContextManager:
        self_event = ModuleEventProxy(self, event)
        return self.notify(self_event)

    @contextmanager
    def notify(self, event: Event):
        self.__check_locking()

        with self.__channel.dispatch(event):
            yield
            _logger.debug(event)

    def __check_locking(self):
        if self.is_locked:
            raise ModuleLockError(f"`{self}` is locked.")

    def __move_module(self, module: Module, priority: Priority):
        last = priority != Priority.HIGH

        try:
            self.__modules.move_to_end(module, last=last)
        except KeyError as exc:
            raise ModuleNotUsedError(
                f"`{module}` can't be found in the modules used by `{self}`."
            ) from exc


"""
InjectedFunction
"""


@dataclass(repr=False, frozen=True, slots=True)
class Dependencies:
    mapping: Mapping[str, Injectable]

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
    def from_mapping(cls, mapping: Mapping[str, Injectable]):
        return cls(mapping=mapping)

    @classmethod
    def empty(cls):
        return cls.from_mapping({})

    @classmethod
    def resolve(cls, signature: Signature, module: Module, owner: type = None):
        dependencies = LazyMapping(cls.__resolver(signature, module, owner))
        return cls.from_mapping(dependencies)

    @classmethod
    def __resolver(
        cls,
        signature: Signature,
        module: Module,
        owner: type = None,
    ) -> Iterator[tuple[str, Injectable]]:
        for name, annotation in cls.__get_annotations(signature, owner):
            try:
                injectable: Injectable = module[annotation]
            except KeyError:
                continue

            yield name, injectable

    @staticmethod
    def __get_annotations(
        signature: Signature,
        owner: type = None,
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


class InjectedFunction(EventListener):
    __slots__ = (
        "__dict__",
        "__signature__",
        "__wrapped__",
        "__dependencies",
        "__owner",
        "__setup_queue",
    )

    def __init__(self, wrapped: Callable[..., Any], /):
        self.__update_vars_from(wrapped)
        update_wrapper(self, wrapped, updated=())
        self.__dependencies = Dependencies.empty()
        self.__owner = None
        self.__setup_queue = LimitedQueue[Callable[[], Any]]()
        self.on_setup(self.__set_signature)

    def __repr__(self) -> str:  # pragma: no cover
        return repr(self.wrapped)

    def __str__(self) -> str:  # pragma: no cover
        return str(self.wrapped)

    def __call__(self, /, *args, **kwargs) -> Any:
        for function in self.__setup_queue:
            function()

        arguments = self.bind(args, kwargs)
        return self.wrapped(*arguments.args, **arguments.kwargs)

    def __get__(self, instance: object = None, owner: type = None):
        if instance is None:
            return self

        return MethodType(self, instance)

    def __set_name__(self, owner: type, name: str):
        self.set_owner(owner)

    @property
    def signature(self) -> Signature:
        return self.__signature__

    @property
    def wrapped(self) -> Callable[..., Any]:
        return self.__wrapped__  # type: ignore

    def bind(
        self,
        args: Iterable[Any] = (),
        kwargs: Mapping[str, Any] = None,
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

    def set_owner(self, owner: type):
        if self.__dependencies.are_resolved:
            raise TypeError(
                "Function owner must be assigned before dependencies are resolved."
            )

        if self.__owner:
            raise TypeError("Function owner is already defined.")

        self.__owner = owner  # type: ignore
        return self

    @synchronized()
    def update(self, module: Module):
        self.__dependencies = Dependencies.resolve(self.signature, module, self.__owner)
        return self

    def on_setup(self, wrapped: Callable[[], Any] = None, /):
        def decorator(wp):
            self.__setup_queue.add(wp)
            return wp

        return decorator(wrapped) if wrapped else decorator

    @singledispatchmethod
    def on_event(self, event: Event, /) -> ContextManager | None:  # type: ignore
        return None

    @on_event.register
    @contextmanager
    def _(self, event: ModuleEvent, /):
        yield
        self.update(event.on_module)

    def __set_signature(self):
        self.__signature__ = inspect.signature(self.wrapped, eval_str=True)
        return self

    def __update_vars_from(self, obj: Any):
        try:
            variables = vars(obj)
        except TypeError:
            pass
        else:
            self.__update_vars(variables)

    def __update_vars(self, variables: Mapping[str, Any]):
        def is_dunder(var: str) -> bool:
            return var.startswith("__") and var.endswith("__")

        restricted_vars = frozenset(var for var in dir(self) if not is_dunder(var))
        vars(self).update(
            (var, value)
            for var, value in variables.items()
            if var not in restricted_vars
        )
