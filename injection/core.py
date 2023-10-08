import inspect
from abc import ABC, abstractmethod
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
    TypeVar,
    get_origin,
)

from injection.exceptions import NoInjectable

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


class UniqueInjectable(Injectable[T]):
    __instance_attribute: str = "_instance"

    __slots__ = (__instance_attribute,)

    def get_instance(self) -> T:
        cls = self.__class__

        try:
            instance = getattr(self, cls.__instance_attribute)
        except AttributeError:
            instance = self.factory()
            object.__setattr__(self, cls.__instance_attribute, instance)

        return instance


@dataclass(repr=False, frozen=True, slots=True)
class InjectionManager:
    __container: dict[type, Injectable] = field(default_factory=dict, init=False)

    def get(self, reference: type) -> Injectable:
        cls = origin if (origin := get_origin(reference)) else reference

        try:
            return self.__container[cls]
        except KeyError as exc:
            raise NoInjectable(f"No injectable for {cls.__name__}.") from exc

    def set_multiple(self, references: Iterable[type], injectable: Injectable):
        new_values = (
            (self.check_if_exists(reference), injectable) for reference in references
        )
        self.__container.update(new_values)
        return self

    def check_if_exists(self, reference: type) -> type:
        if reference in self.__container:
            raise RuntimeError(
                f"An injectable already exists for the "
                f"reference class `{reference.__name__}`."
            )

        return reference


_manager = InjectionManager()


@dataclass(repr=False, frozen=True, slots=True)
class Dependencies:
    __mapping: MappingProxyType[str, Injectable]

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for name, injectable in self.__mapping.items():
            yield name, injectable.get_instance()

    @property
    def arguments(self) -> Mapping[str, Any]:
        return dict(self)

    @classmethod
    def resolve(cls, signature: Signature):
        dependencies = dict(cls.__resolver(signature))
        return cls(MappingProxyType(dependencies))

    @classmethod
    def __resolver(cls, signature: Signature) -> Iterator[tuple[str, Injectable]]:
        for name, parameter in signature.parameters.items():
            try:
                injectable = _manager.get(parameter.annotation)
            except NoInjectable:
                continue

            yield name, injectable


class Arguments(NamedTuple):
    args: Iterable[Any]
    kwargs: Mapping[str, Any]


class Injector:
    __slots__ = ("__function", "__signature", "__dependencies")

    def __init__(self, function: Callable[..., Any]):
        self.__function = function
        self.__signature = None
        self.__dependencies = None

    @property
    def function(self) -> Callable[..., Any]:
        return self.__function

    @property
    def signature(self) -> Signature:
        if self.__signature is None:
            self.__signature = inspect.signature(self.function)

        return self.__signature

    @property
    def dependencies(self) -> Dependencies:
        if self.__dependencies is None:
            self.__dependencies = Dependencies.resolve(self.signature)

        return self.__dependencies

    def bind(self, /, *args, **kwargs) -> Arguments:
        bound = self.signature.bind_partial(*args, **kwargs)
        arguments = self.dependencies.arguments | bound.arguments

        args = []
        kwargs = {}

        for name, parameter in self.signature.parameters.items():
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


@dataclass(repr=False, frozen=True, slots=True)
class Decorator:
    __injectable_class: type[Injectable]

    def __repr__(self) -> str:
        return f"<{self.__injectable_class.__name__} decorator>"  # pragma: no cover

    def __call__(self, wrapped=None, /, reference=None, references=()):
        def decorator(wp):
            def iter_references():
                if isinstance(wp, type):
                    yield wp

                if reference:
                    yield reference

                yield from references

            injectable = self.__injectable_class(wp)
            _manager.set_multiple(
                iter_references(),
                injectable,
            )

            return wp

        return decorator(wrapped) if wrapped else decorator


new = Decorator(NewInjectable)
unique = Decorator(UniqueInjectable)


del (
    Decorator,
    InjectionManager,
    Injectable,
    NewInjectable,
    UniqueInjectable,
)


def get_instance(reference: type[T]) -> T:
    return _manager.get(reference).get_instance()


def inject(function=None, /):
    def decorator(fn):
        injector = Injector(fn)

        @wraps(fn)
        def wrapper(*args, **kwargs):
            arguments = injector.bind(*args, **kwargs)
            return fn(*arguments.args, **arguments.kwargs)

        return wrapper

    return decorator(function) if function else decorator
