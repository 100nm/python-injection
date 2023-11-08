from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass, field
from functools import wraps
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

from injection.common import LazyMapping, Observable, Observation, Observer
from injection.exceptions import NoInjectable

__all__ = ("Module", "new_module")

T = TypeVar("T")


@dataclass(repr=False, frozen=True, slots=True)
class Injectable(Generic[T], ABC):
    __constructor: Callable[..., T]

    def factory(self) -> T:
        return self.__constructor()

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
class Manager(Observable[Any]):
    __container: dict[type, Injectable] = field(default_factory=dict, init=False)
    __observers: set[Observer[Manager]] = field(default_factory=set, init=False)

    @property
    def inject(self) -> InjectDecorator:
        return InjectDecorator(self)

    @property
    def injectable(self) -> InjectableDecorator:
        return InjectableDecorator(self, NewInjectable)

    @property
    def singleton(self) -> InjectableDecorator:
        return InjectableDecorator(self, SingletonInjectable)

    def get(self, __reference: type) -> Injectable:
        cls = origin if (origin := get_origin(__reference)) else __reference

        try:
            return self.__container[cls]
        except KeyError as exc:
            try:
                name = cls.__name__
            except AttributeError:
                name = f"<{type(__reference).__name__} {repr(__reference)}>"

            raise NoInjectable(f"No injectable for {name}.") from exc

    def set_multiple(self, __references: Iterable[type], __injectable: Injectable):
        new_values = (
            (self.check_if_exists(reference), __injectable)
            for reference in __references
        )
        self.__container.update(new_values)
        self.notify()
        return self

    def check_if_exists(self, __reference: type) -> type:
        if __reference in self.__container:
            raise RuntimeError(
                "An injectable already exists for the "
                f"reference class `{__reference.__name__}`."
            )

        return __reference

    def notify(self, _: Any = None, /):
        for observer in self.__observers.copy():
            observer.notify(self)

        return self

    def subscribe(self, observer: Observer):
        self.__observers.add(observer)
        observer.notify(self)
        return self

    def unsubscribe(self, observer: Observer):
        with suppress(KeyError):
            self.__observers.remove(observer)

        return self


@dataclass(repr=False, frozen=True, slots=True)
class Dependencies:
    __mapping: MappingProxyType[str, Injectable]

    def __bool__(self) -> bool:
        return bool(self.__mapping)

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for name, injectable_object in self.__mapping.items():
            yield name, injectable_object.get_instance()

    @property
    def arguments(self) -> Mapping[str, Any]:
        return dict(self)

    @classmethod
    def from_mapping(cls, __mapping: Mapping[str, Injectable]):
        return cls(MappingProxyType(__mapping))

    @classmethod
    def empty(cls):
        return cls.from_mapping({})

    @classmethod
    def resolve(cls, __signature: Signature, __manager: Manager):
        dependencies = LazyMapping(cls.__resolver(__signature, __manager))
        return cls.from_mapping(dependencies)

    @classmethod
    def __resolver(
        cls,
        __signature: Signature,
        __manager: Manager,
    ) -> Iterator[tuple[str, Injectable]]:
        for name, parameter in __signature.parameters.items():
            try:
                injectable_object = __manager.get(parameter.annotation)
            except NoInjectable:
                continue

            yield name, injectable_object


class Arguments(NamedTuple):
    args: Iterable[Any]
    kwargs: Mapping[str, Any]


class Binder(Observer[Manager]):
    __slots__ = ("__signature", "__dependencies")

    def __init__(self, __callable: Callable[..., Any]):
        self.__signature = inspect.signature(__callable)
        self.__dependencies = Dependencies.empty()

    def bind(self, /, *__args, **__kwargs) -> Arguments:
        if not self.__dependencies:
            return Arguments(__args, __kwargs)

        bound = self.__signature.bind_partial(*__args, **__kwargs)
        arguments = self.__dependencies.arguments | bound.arguments

        args = []
        kwargs = {}

        for name, parameter in self.__signature.parameters.items():
            try:
                value = arguments.pop(name)
            except KeyError:
                continue

            match parameter.kind:
                case Parameter.POSITIONAL_ONLY:
                    args.append(value)
                case Parameter.VAR_POSITIONAL:
                    args.extend(value)
                case Parameter.VAR_KEYWORD:
                    kwargs.update(value)
                case _:
                    kwargs[name] = value

        return Arguments(tuple(args), kwargs)

    def notify(self, __manager: Manager, /):
        self.__dependencies = Dependencies.resolve(self.__signature, __manager)
        return self


@final
@dataclass(repr=False, frozen=True, slots=True)
class InjectDecorator:
    __manager: Manager

    def __call__(self, wrapped=None, /):
        def decorator(wp):
            if isinstance(wp, type):
                return self.__class_decorator(wp)

            return self.__decorator(wp)

        return decorator(wrapped) if wrapped else decorator

    def __decorator(self, __function: Callable[..., Any], /) -> Callable[..., Any]:
        binder = Binder(__function)
        observation = Observation(binder, self.__manager)
        observation.subscribe()

        @wraps(__function)
        def wrapper(*args, **kwargs):
            observation.keep()
            arguments = binder.bind(*args, **kwargs)
            return __function(*arguments.args, **arguments.kwargs)

        return wrapper

    def __class_decorator(self, __type: type, /) -> type:
        init_function = type.__getattribute__(__type, "__init__")
        type.__setattr__(__type, "__init__", self.__decorator(init_function))
        return __type


@final
@dataclass(repr=False, frozen=True, slots=True)
class InjectableDecorator:
    __manager: Manager
    __class: type[Injectable]

    def __repr__(self) -> str:
        return f"<{self.__class.__name__} decorator>"  # pragma: no cover

    def __call__(
        self,
        wrapped=None,
        /,
        reference=None,
        references=(),
        auto_inject=True,
    ):
        def decorator(wp):
            if auto_inject:
                wp = self.__manager.inject(wp)

            @lambda fn: fn()
            def iter_references():
                if isinstance(wp, type):
                    yield wp

                if reference:
                    yield reference

                yield from references

            injectable_object = self.__class(wp)
            self.__manager.set_multiple(
                iter_references,
                injectable_object,
            )

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
    manager: Manager = field(default_factory=Manager, init=False)

    @property
    def inject(self) -> InjectDecorator:
        return self.manager.inject

    @property
    def injectable(self) -> InjectableDecorator:
        return self.manager.injectable

    @property
    def singleton(self) -> InjectableDecorator:
        return self.manager.singleton

    def get_instance(self, reference: type[T]) -> T:
        instance = self.manager.get(reference).get_instance()
        return cast(reference, instance)


def new_module() -> Module:
    module = InjectionModule()
    return cast(Module, module)
