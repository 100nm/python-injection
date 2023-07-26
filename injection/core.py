import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property, wraps
from inspect import Parameter
from typing import Callable, Generic, Iterable, TypeVar

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
    def get_instance(self) -> T:
        return self.factory()


class UniqueInjectable(Injectable[T]):
    @cached_property
    def __instance(self) -> T:
        return self.factory()

    def get_instance(self) -> T:
        return self.__instance


@dataclass(repr=False, frozen=True, slots=True)
class InjectionManager:
    __container: dict[type, Injectable] = field(default_factory=dict, init=False)

    def get(self, reference: type) -> Injectable:
        try:
            return self.__container[reference]
        except KeyError as exc:
            raise NoInjectable(f"No injectable for {reference.__name__}.") from exc

    def set_multiple(self, references: Iterable[type], injectable: Injectable):
        def reference_parser():
            for reference in references:
                self.check_if_exists(reference)
                yield reference, injectable

        new_values = reference_parser()
        self.__container.update(new_values)

    def check_if_exists(self, reference: type):
        if reference in self.__container:
            raise RuntimeError(
                f"An injectable already exists for the "
                f"reference class `{reference.__name__}`."
            )


_manager = InjectionManager()

del InjectionManager


@dataclass(repr=False, frozen=True, slots=True)
class Decorator:
    __injectable_class: type[Injectable]

    def __repr__(self) -> str:
        return f"<{self.__injectable_class.__name__} decorator>"  # pragma: no cover

    def __call__(self, wp=None, /, **kwargs):
        def decorator(wrapped):
            def iter_references():
                if isinstance(wrapped, type):
                    yield wrapped

                if reference := kwargs.pop("reference", None):
                    yield reference

                for reference in kwargs.pop("references", ()):
                    yield reference

            references = iter_references()
            injectable = self.__injectable_class(wrapped)
            _manager.set_multiple(references, injectable)

            return wrapped

        return decorator(wp) if wp else decorator


new = Decorator(NewInjectable)
unique = Decorator(UniqueInjectable)

del Decorator


def get_instance(reference: type[T]) -> T:
    return _manager.get(reference).get_instance()


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
                    value = arguments.pop(name)
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
                        kwargs.update(value)
                    case _:
                        kwargs[name] = value

            return function(*args, **kwargs)

        return wrapper

    return decorator(fn) if fn else decorator
