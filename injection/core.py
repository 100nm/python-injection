import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property, wraps
from inspect import Parameter
from typing import Generic, NamedTuple, TypeVar

T = TypeVar("T")


@dataclass(repr=False, frozen=True, slots=True)
class Injectable(Generic[T], ABC):
    cls: type[T]

    def __repr__(self) -> str:
        return f"<{self.cls.__name__} injectable>"

    def factory(self) -> T:
        return self.cls()

    @abstractmethod
    def get_instance(self) -> T:
        raise NotImplementedError


class NewInjectable(Injectable[T]):
    def get_instance(self) -> T:
        return self.factory()


class UniqueInjectable(Injectable[T]):
    @cached_property
    def __instance(self) -> T:
        return self.factory()

    def get_instance(self) -> T:
        return self.__instance


class NoInjectable(Exception):
    ...


@dataclass(repr=False, frozen=True, slots=True)
class InjectionManager:
    __injectables: dict[type, Injectable] = field(default_factory=dict, init=False)

    def __getitem__(self, reference: type) -> Injectable:
        try:
            return self.__injectables[reference]
        except KeyError as exc:
            raise NoInjectable(f"No injectable for {reference.__name__}.") from exc

    def __setitem__(self, reference: type, injectable: Injectable):
        if not issubclass(injectable.cls, reference):
            raise TypeError(
                f"`{injectable.cls.__name__}` isn't a subclass of "
                f"reference class `{reference.__name__}`."
            )

        if reference in self.__injectables:
            raise RuntimeError(
                f"An injectable already exists for the "
                f"reference class `{reference.__name__}`."
            )

        self.__injectables[reference] = injectable


_manager = InjectionManager()

del InjectionManager


class Decorator(NamedTuple):
    injectable_class: type[Injectable]

    def __repr__(self) -> str:
        return f"<{self.injectable_class.__name__} decorator>"

    def __call__(self, cls=None, /, **kwargs):
        def wrap(cls):
            injectable = self.injectable_class(cls)
            _manager[cls] = injectable

            if reference := kwargs.pop("reference", None):
                _manager[reference] = injectable

            for reference in kwargs.pop("references", ()):
                _manager[reference] = injectable

            return cls

        return wrap(cls) if cls else wrap


new = Decorator(NewInjectable)
unique = Decorator(UniqueInjectable)

del Decorator


def get_instance(reference: type[T]) -> T:
    return _manager[reference].get_instance()


def inject(fn=None):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            signature = inspect.signature(function)
            arguments = signature.bind_partial(*args, **kwargs).arguments
            args = []
            kwargs = {}

            for name, parameter in signature.parameters.items():
                try:
                    value = arguments[name]
                except KeyError:
                    try:
                        value = get_instance(parameter.annotation)
                    except NoInjectable:
                        continue

                match parameter.kind:
                    case Parameter.POSITIONAL_ONLY:
                        args.append(value)
                    case Parameter.VAR_POSITIONAL:
                        args.extend(value)
                    case Parameter.VAR_KEYWORD:
                        kwargs |= value
                    case _:
                        kwargs[name] = value

            return function(*args, **kwargs)

        return wrapper

    return decorator(fn) if fn else decorator
