from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections import ChainMap, OrderedDict
from contextlib import ContextDecorator, contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import cached_property, singledispatchmethod, wraps
from inspect import Signature, get_annotations
from logging import getLogger
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
    Protocol,
    TypeVar,
    cast,
    final,
    get_origin,
    runtime_checkable,
)

from injection.common.event import Event, EventChannel, EventListener
from injection.common.lazy import Lazy, LazyMapping
from injection.exceptions import (
    ModuleCircularUseError,
    ModuleError,
    ModuleNotUsedError,
    NoInjectable,
)

__all__ = ("Injectable", "Module", "ModulePriorities")

_logger = getLogger(__name__)

T = TypeVar("T")


def _format_type(cls: type) -> str:
    try:
        return f"{cls.__module__}.{cls.__qualname__}"
    except AttributeError:
        return str(cls)


"""
Events
"""


@dataclass(frozen=True, slots=True)
class ContainerEvent(Event, ABC):
    on_container: Container


@dataclass(frozen=True, slots=True)
class ContainerDependenciesUpdated(ContainerEvent):
    references: set[type]

    def __str__(self) -> str:
        length = len(self.references)
        formatted_references = ", ".join(
            f"`{_format_type(reference)}`" for reference in self.references
        )
        return (
            f"{length} container dependenc{'ies' if length > 1 else 'y'} have been "
            f"updated{f': {formatted_references}' if formatted_references else ''}."
        )


@dataclass(frozen=True, slots=True)
class ModuleEvent(Event, ABC):
    on_module: Module


@dataclass(frozen=True, slots=True)
class ModuleEventProxy(ModuleEvent):
    event: Event

    def __str__(self) -> str:
        return f"`{self.on_module}` has propagated an event: {self.origin}"

    def __iter__(self) -> Iterator[Event]:
        if isinstance(self.event, ModuleEventProxy):
            yield from self.event

        yield self.event

    @property
    def origin(self) -> Event:
        return next(self.__iter__())

    @property
    def is_circular(self) -> bool:
        return any(
            isinstance(event, ModuleEvent) and event.on_module is self.on_module
            for event in self
        )

    @property
    def previous_module(self) -> Module | None:
        if isinstance(self.event, ModuleEvent):
            return self.event.on_module

        return None


@dataclass(frozen=True, slots=True)
class ModuleAdded(ModuleEvent):
    module_added: Module

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
    priority: ModulePriorities

    def __str__(self) -> str:
        return (
            f"In `{self.on_module}`, the priority `{self.priority.name}` "
            f"has been applied to `{self.module_updated}`."
        )


"""
Injectables
"""


@runtime_checkable
class Injectable(Protocol[T]):
    __slots__ = ()

    @abstractmethod
    def get_instance(self) -> T:
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class _BaseInjectable(Injectable[T], ABC):
    factory: Callable[[], T]


class NewInjectable(_BaseInjectable[T]):
    __slots__ = ()

    def get_instance(self) -> T:
        return self.factory()


class SingletonInjectable(_BaseInjectable[T]):
    @cached_property
    def __instance(self) -> T:
        return self.factory()

    def get_instance(self) -> T:
        return self.__instance


"""
Container
"""


@dataclass(repr=False, frozen=True, slots=True)
class Container:
    __data: dict[type, Injectable] = field(default_factory=dict, init=False)
    __channel: EventChannel = field(default_factory=EventChannel, init=False)

    def __getitem__(self, reference: type[T]) -> Injectable[T]:
        cls = self.__get_origin(reference)

        try:
            return self.__data[cls]
        except KeyError as exc:
            raise NoInjectable(f"No injectable for `{_format_type(cls)}`.") from exc

    def set_multiple(self, references: Iterable[type], injectable: Injectable):
        references = set(self.__get_origin(reference) for reference in references)

        if references:
            new_values = (
                (self.check_if_exists(reference), injectable)
                for reference in references
            )
            self.__data.update(new_values)
            event = ContainerDependenciesUpdated(self, references)
            self.notify(event)

        return self

    def check_if_exists(self, reference: type) -> type:
        if reference in self.__data:
            raise RuntimeError(
                "An injectable already exists for the reference "
                f"class `{_format_type(reference)}`."
            )

        return reference

    def add_listener(self, listener: EventListener):
        self.__channel.add_listener(listener)
        return self

    def notify(self, event: Event):
        self.__channel.dispatch(event)
        return self

    @staticmethod
    def __get_origin(cls: type) -> type:
        if origin := get_origin(cls):
            return origin

        return cls


"""
Module
"""


class ModulePriorities(Enum):
    HIGH = auto()
    LOW = auto()


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class Module(EventListener):
    """
    Object with isolated injection environment.

    Modules have been designed to simplify unit test writing. So think carefully before
    instantiating a new one. They could increase complexity unnecessarily if used
    extensively.
    """

    name: str = field(default=None)
    __container: Container = field(default_factory=Container, init=False)
    __channel: EventChannel = field(default_factory=EventChannel, init=False)
    __modules: OrderedDict[Module, None] = field(
        default_factory=OrderedDict,
        init=False,
    )

    def __post_init__(self):
        self.__container.add_listener(self)

    def __getitem__(self, reference: type[T], /) -> Injectable[T]:
        return ChainMap(*self.__modules, self.__container)[reference]

    def __setitem__(self, on: type | Iterable[type], injectable: Injectable, /):
        references = on if isinstance(on, Iterable) else (on,)
        self.__container.set_multiple(references, injectable)

    def __str__(self) -> str:
        return self.name or object.__str__(self)

    @property
    def inject(self) -> InjectDecorator:
        """
        Decorator applicable to a class or function. Inject function dependencies using
        parameter type annotations. If applied to a class, the dependencies resolved
        will be those of the `__init__` method.
        """

        return InjectDecorator(self)

    @property
    def injectable(self) -> InjectableDecorator:
        """
        Decorator applicable to a class or function. It is used to indicate how the
        injectable will be constructed. At injection time, a new instance will be
        injected each time. Automatically injects constructor dependencies, can be
        disabled with `auto_inject=False`.
        """

        return InjectableDecorator(self, NewInjectable)

    @property
    def singleton(self) -> InjectableDecorator:
        """
        Decorator applicable to a class or function. It is used to indicate how the
        singleton will be constructed. At injection time, the injected instance will
        always be the same. Automatically injects constructor dependencies, can be
        disabled with `auto_inject=False`.
        """

        return InjectableDecorator(self, SingletonInjectable)

    def get_instance(self, reference: type[T]) -> T | None:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or return `None`.
        """

        try:
            injectable = self[reference]
        except KeyError:
            return None

        instance = injectable.get_instance()
        return cast(reference, instance)

    def use(
        self,
        module: Module,
        priority: ModulePriorities = ModulePriorities.LOW,
    ):
        """
        Function for using another module. Using another module replaces the module's
        dependencies with those of the module used. If the dependency is not found, it
        will be searched for in the module's dependency container.
        """

        if module is self:
            raise ModuleError("Module can't be used by itself.")

        if module in self.__modules:
            raise ModuleError(f"`{self}` already uses `{module}`.")

        self.__modules[module] = None
        self.__move_module(module, priority)
        module.add_listener(self)
        event = ModuleAdded(self, module)
        self.notify(event)
        return self

    def stop_using(self, module: Module):
        """
        Function to remove a module in use.
        """

        try:
            self.__modules.pop(module)
        except KeyError:
            ...
        else:
            module.remove_listener(self)
            event = ModuleRemoved(self, module)
            self.notify(event)

        return self

    @contextmanager
    def use_temporarily(
        self,
        module: Module,
        priority: ModulePriorities = ModulePriorities.LOW,
    ) -> ContextDecorator:
        """
        Context manager or decorator for temporary use of a module.
        """

        self.use(module, priority)
        yield
        self.stop_using(module)

    def change_priority(self, module: Module, priority: ModulePriorities):
        """
        Function for changing the priority of a module in use.
        There are two priority values:

        * **LOW**: The module concerned becomes the least important of the modules used.
        * **HIGH**: The module concerned becomes the most important of the modules used.
        """

        self.__move_module(module, priority)
        event = ModulePriorityUpdated(self, module, priority)
        self.notify(event)
        return self

    def add_listener(self, listener: EventListener):
        self.__channel.add_listener(listener)
        return self

    def remove_listener(self, listener: EventListener):
        self.__channel.remove_listener(listener)
        return self

    def on_event(self, event: Event, /):
        self_event = ModuleEventProxy(self, event)

        if self_event.is_circular:
            raise ModuleCircularUseError(
                "Circular dependency between two modules: "
                f"`{self_event.previous_module}` and `{self}`."
            )

        self.notify(self_event)

    def notify(self, event: Event):
        _logger.debug(f"{event}")
        self.__channel.dispatch(event)
        return self

    def __move_module(self, module: Module, priority: ModulePriorities):
        last = priority == ModulePriorities.LOW

        try:
            self.__modules.move_to_end(module, last=last)
        except KeyError as exc:
            raise ModuleNotUsedError(
                f"`{module}` can't be found in the modules used by `{self}`."
            ) from exc


"""
Binder
"""


@dataclass(repr=False, frozen=True, slots=True)
class Dependencies:
    __mapping: MappingProxyType[str, Injectable]

    def __bool__(self) -> bool:
        return bool(self.__mapping)

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for name, injectable in self.__mapping.items():
            yield name, injectable.get_instance()

    @property
    def arguments(self) -> Mapping[str, Any]:
        return dict(self)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Injectable]):
        return cls(MappingProxyType(mapping))

    @classmethod
    def empty(cls):
        return cls.from_mapping({})

    @classmethod
    def resolve(cls, signature: Signature, module: Module):
        dependencies = LazyMapping(cls.__resolver(signature, module))
        return cls.from_mapping(dependencies)

    @classmethod
    def __resolver(
        cls,
        signature: Signature,
        module: Module,
    ) -> Iterator[tuple[str, Injectable]]:
        for name, parameter in signature.parameters.items():
            try:
                injectable = module[parameter.annotation]
            except KeyError:
                continue

            yield name, injectable


class Arguments(NamedTuple):
    args: Iterable[Any]
    kwargs: Mapping[str, Any]


class Binder(EventListener):
    __slots__ = ("__signature", "__dependencies")

    def __init__(self, signature: Signature):
        self.__signature = signature
        self.__dependencies = Dependencies.empty()

    def bind(self, /, *args, **kwargs) -> Arguments:
        if not self.__dependencies:
            return Arguments(args, kwargs)

        bound = self.__signature.bind_partial(*args, **kwargs)
        bound.arguments = self.__dependencies.arguments | bound.arguments
        return Arguments(bound.args, bound.kwargs)

    def update(self, module: Module):
        self.__dependencies = Dependencies.resolve(self.__signature, module)
        return self

    @singledispatchmethod
    def on_event(self, event: Event, /):
        ...

    @on_event.register
    def _(self, event: ModuleEvent, /):
        self.update(event.on_module)


"""
Decorators
"""


@final
@dataclass(repr=False, frozen=True, slots=True)
class InjectDecorator:
    __module: Module

    def __call__(self, wrapped: Callable[..., Any] = None, /):
        def decorator(wp):
            if isinstance(wp, type):
                return self.__class_decorator(wp)

            return self.__decorator(wp)

        return decorator(wrapped) if wrapped else decorator

    def __decorator(self, function: Callable[..., Any], /) -> Callable[..., Any]:
        lazy_binder = Lazy[Binder](lambda: self.__new_binder(function))

        @wraps(function)
        def wrapper(*args, **kwargs):
            arguments = lazy_binder.value.bind(*args, **kwargs)
            return function(*arguments.args, **arguments.kwargs)

        return wrapper

    def __class_decorator(self, cls: type, /) -> type:
        init_function = type.__getattribute__(cls, "__init__")
        type.__setattr__(cls, "__init__", self.__decorator(init_function))
        return cls

    def __new_binder(self, function: Callable[..., Any]) -> Binder:
        signature = inspect.signature(function, eval_str=True)
        binder = Binder(signature).update(self.__module)
        self.__module.add_listener(binder)
        return binder


@final
@dataclass(repr=False, frozen=True, slots=True)
class InjectableDecorator:
    __module: Module
    __class: type[_BaseInjectable]

    def __repr__(self) -> str:
        return f"<{self.__class.__qualname__} decorator>"

    def __call__(
        self,
        wrapped: Callable[..., Any] = None,
        /,
        on: type | Iterable[type] = None,
        auto_inject: bool = True,
    ):
        def decorator(wp):
            if auto_inject:
                wp = self.__module.inject(wp)

            @lambda fn: fn()
            def references():
                if reference := self.__get_reference(wp):
                    yield reference

                if on is None:
                    return
                elif isinstance(on, Iterable):
                    yield from on
                else:
                    yield on

            self.__module[references] = self.__class(wp)
            return wp

        return decorator(wrapped) if wrapped else decorator

    @staticmethod
    def __get_reference(wrapped: Callable[..., Any], /) -> type | None:
        if isinstance(wrapped, type):
            return wrapped

        elif callable(wrapped):
            return_type = get_annotations(wrapped, eval_str=True).get("return")

            if isinstance(return_type, type):
                return return_type

        return None
