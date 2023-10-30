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


class SingletonInjectable(Injectable[T]):
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
class Manager:
    __container: dict[type, Injectable] = field(default_factory=dict, init=False)

    def get(self, __reference: type) -> Injectable:
        cls = origin if (origin := get_origin(__reference)) else __reference

        try:
            return self.__container[cls]
        except KeyError as exc:
            try:
                name = cls.__name__
            except AttributeError:  # pragma: no cover
                name = repr(__reference)

            raise NoInjectable(f"No injectable for {name}.") from exc

    def set_multiple(self, __references: Iterable[type], __injectable: Injectable):
        new_values = (
            (self.check_if_exists(reference), __injectable)
            for reference in __references
        )
        self.__container.update(new_values)
        return self

    def check_if_exists(self, __reference: type) -> type:
        if __reference in self.__container:
            raise RuntimeError(
                f"An injectable already exists for the "
                f"reference class `{__reference.__name__}`."
            )

        return __reference


class ManagerGetter:
    __slots__ = ("__default",)

    def __init__(self):
        self.__default = self.__manager_factory()

    def __call__(self) -> Manager:
        return self.__default

    @classmethod
    def __manager_factory(cls) -> Manager:
        return Manager()


@dataclass(repr=False, frozen=True, slots=True)
class Dependencies:
    __mapping: MappingProxyType[str, Injectable]

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for name, injectable_object in self.__mapping.items():
            yield name, injectable_object.get_instance()

    @property
    def arguments(self) -> Mapping[str, Any]:
        return dict(self)

    @classmethod
    def resolve(cls, __signature: Signature):
        dependencies = dict(cls.__resolver(__signature))
        return cls(MappingProxyType(dependencies))

    @classmethod
    def __resolver(cls, __signature: Signature) -> Iterator[tuple[str, Injectable]]:
        manager = _get_manager()

        for name, parameter in __signature.parameters.items():
            try:
                injectable_object = manager.get(parameter.annotation)
            except NoInjectable:
                continue

            yield name, injectable_object


class Arguments(NamedTuple):
    args: Iterable[Any]
    kwargs: Mapping[str, Any]


class Binder:
    __slots__ = ("__callable", "__signature", "__dependencies")

    def __init__(self, __callable: Callable[..., Any], /):
        self.__callable = __callable
        self.__signature = None
        self.__dependencies = None

    @property
    def callable(self) -> Callable[..., Any]:
        return self.__callable

    @property
    def signature(self) -> Signature:
        if self.__signature is None:
            self.__signature = inspect.signature(self.callable)

        return self.__signature

    @property
    def dependencies(self) -> Dependencies:
        if self.__dependencies is None:
            self.__dependencies = Dependencies.resolve(self.signature)

        return self.__dependencies

    def bind(self, /, *__args, **__kwargs) -> Arguments:
        bound = self.signature.bind_partial(*__args, **__kwargs)
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
class InjectDecorator:
    def __call__(self, wrapped=None, /):
        def decorator(wp):
            if isinstance(wp, type):
                return self.__class_decorator(wp)

            return self.__decorator(wp)

        return decorator(wrapped) if wrapped else decorator

    @classmethod
    def __decorator(cls, __function: Callable[..., Any], /) -> Callable[..., Any]:
        binder = Binder(__function)

        @wraps(__function)
        def wrapper(*args, **kwargs):
            arguments = binder.bind(*args, **kwargs)
            return __function(*arguments.args, **arguments.kwargs)

        return wrapper

    @classmethod
    def __class_decorator(cls, __type: type, /) -> type:
        init_function = type.__getattribute__(__type, "__init__")
        type.__setattr__(__type, "__init__", cls.__decorator(init_function))
        return __type


@dataclass(repr=False, frozen=True, slots=True)
class InjectableDecorator:
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
                wp = inject(wp)

            @lambda fn: fn()
            def iter_references():
                if isinstance(wp, type):
                    yield wp

                if reference:
                    yield reference

                yield from references

            injectable_object = self.__class(wp)
            _get_manager().set_multiple(
                iter_references,
                injectable_object,
            )

            return wp

        return decorator(wrapped) if wrapped else decorator


_get_manager = ManagerGetter()

inject = InjectDecorator()
injectable = InjectableDecorator(NewInjectable)
singleton = InjectableDecorator(SingletonInjectable)


def get_instance(reference: type[T]) -> T:
    return _get_manager().get(reference).get_instance()


del (
    Injectable,
    InjectableDecorator,
    InjectDecorator,
    ManagerGetter,
    NewInjectable,
    SingletonInjectable,
    T,
)

__all__ = (
    "get_instance",
    "inject",
    "injectable",
    "singleton",
)
