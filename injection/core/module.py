from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import singledispatchmethod, wraps
from inspect import Parameter, Signature
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    Generic,
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
from injection.common.lazy import LazyMapping
from injection.exceptions import NoInjectable

__all__ = ("Module", "new_module")

T = TypeVar("T")


@dataclass(repr=False, frozen=True, slots=True)
class Injectable(Generic[T], ABC):
    factory: Callable[[], T]

    @abstractmethod
    def get_instance(self) -> T:
        raise NotImplementedError


class NewInjectable(Injectable[T]):
    __slots__ = ()

    def get_instance(self) -> T:
        return self.factory()


class SingletonInjectable(Injectable[T]):
    __instance_attribute: str = "_instance"

    __slots__ = (__instance_attribute,)

    def get_instance(self) -> T:
        cls = type(self)

        try:
            instance = getattr(self, cls.__instance_attribute)
        except AttributeError:
            instance = self.factory()
            object.__setattr__(self, cls.__instance_attribute, instance)

        return instance


@dataclass(repr=False, frozen=True, slots=True)
class ContainerUpdated(Event):
    container: Container


@dataclass(repr=False, frozen=True, slots=True)
class Container:
    __data: dict[type, Injectable] = field(default_factory=dict, init=False)
    __channel: EventChannel = field(default_factory=EventChannel, init=False)

    def __getitem__(self, reference: type) -> Injectable:
        cls = origin if (origin := get_origin(reference)) else reference

        try:
            return self.__data[cls]
        except KeyError as exc:
            try:
                name = f"{cls.__module__}.{cls.__qualname__}"
            except AttributeError:
                name = repr(reference)

            raise NoInjectable(f"No injectable for `{name}`.") from exc

    @property
    def inject(self) -> InjectDecorator:
        return InjectDecorator(self)

    @property
    def injectable(self) -> InjectableDecorator:
        return InjectableDecorator(self, NewInjectable)

    @property
    def singleton(self) -> InjectableDecorator:
        return InjectableDecorator(self, SingletonInjectable)

    def set_multiple(self, references: Iterable[type], injectable: Injectable):
        new_values = (
            (self.check_if_exists(reference), injectable) for reference in references
        )
        self.__data.update(new_values)
        self.__notify()
        return self

    def check_if_exists(self, reference: type) -> type:
        if reference in self.__data:
            raise RuntimeError(
                "An injectable already exists for the "
                f"reference class `{reference.__name__}`."
            )

        return reference

    def add_listener(self, listener: EventListener):
        self.__channel.add_listener(listener)
        return self

    def __notify(self):
        event = ContainerUpdated(self)
        self.__channel.dispatch(event)
        return self


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
    def resolve(cls, signature: Signature, container: Container):
        dependencies = LazyMapping(cls.__resolver(signature, container))
        return cls.from_mapping(dependencies)

    @classmethod
    def __resolver(
        cls,
        signature: Signature,
        container: Container,
    ) -> Iterator[tuple[str, Injectable]]:
        for name, parameter in signature.parameters.items():
            try:
                injectable = container[parameter.annotation]
            except NoInjectable:
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
        arguments = self.__dependencies.arguments | bound.arguments

        positional = []
        keywords = {}

        for name, parameter in self.__signature.parameters.items():
            try:
                value = arguments.pop(name)
            except KeyError:
                continue

            match parameter.kind:
                case Parameter.POSITIONAL_ONLY:
                    positional.append(value)
                case Parameter.VAR_POSITIONAL:
                    positional.extend(value)
                case Parameter.VAR_KEYWORD:
                    keywords.update(value)
                case _:
                    keywords[name] = value

        return Arguments(tuple(positional), keywords)

    def update(self, container: Container):
        self.__dependencies = Dependencies.resolve(self.__signature, container)
        return self

    @singledispatchmethod
    def on_event(self, event: Event, /):
        ...  # pragma: no cover

    @on_event.register
    def _(self, event: ContainerUpdated, /):
        self.update(event.container)


@final
@dataclass(repr=False, frozen=True, slots=True)
class InjectDecorator:
    __container: Container

    def __call__(self, wrapped=None, /):
        def decorator(wp):
            if isinstance(wp, type):
                return self.__class_decorator(wp)

            return self.__decorator(wp)

        return decorator(wrapped) if wrapped else decorator

    def __decorator(self, function: Callable[..., Any], /) -> Callable[..., Any]:
        signature = inspect.signature(function)
        binder = Binder(signature).update(self.__container)
        self.__container.add_listener(binder)

        @wraps(function)
        def wrapper(*args, **kwargs):
            arguments = binder.bind(*args, **kwargs)
            return function(*arguments.args, **arguments.kwargs)

        return wrapper

    def __class_decorator(self, cls: type, /) -> type:
        init_function = type.__getattribute__(cls, "__init__")
        type.__setattr__(cls, "__init__", self.__decorator(init_function))
        return cls


@final
@dataclass(repr=False, frozen=True, slots=True)
class InjectableDecorator:
    __container: Container
    __class: type[Injectable]

    def __repr__(self) -> str:
        return f"<{self.__class.__name__} decorator>"  # pragma: no cover

    def __call__(self, wrapped=None, /, on=None, auto_inject=True):
        def decorator(wp):
            if auto_inject:
                wp = self.__container.inject(wp)

            @lambda fn: fn()
            def references():
                if isinstance(wp, type):
                    yield wp

                if on is None:
                    return
                elif isinstance(on, Iterable):
                    yield from on
                else:
                    yield on

            injectable = self.__class(wp)
            self.__container.set_multiple(references, injectable)

            return wp

        return decorator(wrapped) if wrapped else decorator


@runtime_checkable
class Module(Protocol):
    __slots__ = ()

    @abstractmethod
    def get_instance(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def inject(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def injectable(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def singleton(self, *args, **kwargs):
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class InjectionModule:
    __container: Container = field(default_factory=Container, init=False)

    @property
    def inject(self) -> InjectDecorator:
        return self.__container.inject

    @property
    def injectable(self) -> InjectableDecorator:
        return self.__container.injectable

    @property
    def singleton(self) -> InjectableDecorator:
        return self.__container.singleton

    def get_instance(self, reference: type[T]) -> T:
        instance = self.__container[reference].get_instance()
        return cast(reference, instance)


def new_module() -> Module:
    module = InjectionModule()
    return cast(Module, module)
