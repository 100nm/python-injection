from abc import abstractmethod
from collections.abc import Callable, Iterable
from contextlib import ContextDecorator
from enum import Enum
from types import UnionType
from typing import (
    Any,
    ContextManager,
    Final,
    Literal,
    Protocol,
    TypeVar,
    final,
    runtime_checkable,
)

from .common.invertible import Invertible

_In_T = TypeVar("_In_T", covariant=False)
_Co_T = TypeVar("_Co_T", covariant=True)

default_module: Final[Module] = ...

get_instance = default_module.get_instance
get_lazy_instance = default_module.get_lazy_instance
inject = default_module.inject
injectable = default_module.injectable
set_constant = default_module.set_constant
should_be_injectable = default_module.should_be_injectable
singleton = default_module.singleton

@final
class Module:
    """
    Object with isolated injection environment.

    Modules have been designed to simplify unit test writing. So think carefully before
    instantiating a new one. They could increase complexity unnecessarily if used
    extensively.
    """

    def __init__(self, name: str = ...): ...
    def __contains__(self, cls: type | UnionType, /) -> bool: ...
    def inject(self, wrapped: Callable[..., Any] = ..., /):
        """
        Decorator applicable to a class or function. Inject function dependencies using
        parameter type annotations. If applied to a class, the dependencies resolved
        will be those of the `__init__` method.
        """

    def injectable(
        self,
        wrapped: Callable[..., Any] = ...,
        /,
        *,
        cls: type[Injectable] = ...,
        inject: bool = ...,
        on: type | Iterable[type] | UnionType = ...,
        mode: InjectableMode | Literal["fallback", "normal", "override"] = ...,
    ):
        """
        Decorator applicable to a class or function. It is used to indicate how the
        injectable will be constructed. At injection time, a new instance will be
        injected each time.
        """

    def singleton(
        self,
        wrapped: Callable[..., Any] = ...,
        /,
        *,
        inject: bool = ...,
        on: type | Iterable[type] | UnionType = ...,
        mode: InjectableMode | Literal["fallback", "normal", "override"] = ...,
    ):
        """
        Decorator applicable to a class or function. It is used to indicate how the
        singleton will be constructed. At injection time, the injected instance will
        always be the same.
        """

    def should_be_injectable(self, wrapped: type = ..., /):
        """
        Decorator applicable to a class. It is used to specify whether an injectable
        should be registered. Raise an exception at injection time if the class isn't
        registered.
        """

    def set_constant(
        self,
        instance: _In_T,
        on: type | Iterable[type] | UnionType = ...,
        *,
        mode: InjectableMode | Literal["fallback", "normal", "override"] = ...,
    ) -> _In_T:
        """
        Function for registering a specific instance to be injected. This is useful for
        registering global variables. The difference with the singleton decorator is
        that no dependencies are resolved, so the module doesn't need to be locked.
        """

    def resolve(self, cls: type[_In_T]) -> _In_T:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or an exception will be raised.
        """

    def get_instance(self, cls: type[_In_T]) -> _In_T | None:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or return `None`.
        """

    def get_lazy_instance(
        self,
        cls: type[_In_T],
        *,
        cache: bool = ...,
    ) -> Invertible[_In_T | None]:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or `None`. Return a `Invertible` object. To access the instance
        contained in an invertible object, simply use a wavy line (~).
        With `cache=True`, the instance retrieved will always be the same.

        Example: instance = ~lazy_instance
        """

    def use(
        self,
        module: Module,
        *,
        priority: ModulePriority | Literal["low", "high"] = ...,
    ):
        """
        Function for using another module. Using another module replaces the module's
        dependencies with those of the module used. If the dependency is not found, it
        will be searched for in the module's dependency container.
        """

    def stop_using(self, module: Module):
        """
        Function to remove a module in use.
        """

    def use_temporarily(
        self,
        module: Module,
        *,
        priority: ModulePriority | Literal["low", "high"] = ...,
    ) -> ContextManager | ContextDecorator:
        """
        Context manager or decorator for temporary use of a module.
        """

    def change_priority(
        self,
        module: Module,
        priority: ModulePriority | Literal["low", "high"],
    ):
        """
        Function for changing the priority of a module in use.
        There are two priority values:

        * **LOW**: The module concerned becomes the least important of the modules used.
        * **HIGH**: The module concerned becomes the most important of the modules used.
        """

    def unlock(self):
        """
        Function to unlock the module by deleting cached instances of singletons.
        """

@final
class ModulePriority(str, Enum):
    LOW = ...
    HIGH = ...

@runtime_checkable
class Injectable(Protocol[_Co_T]):
    def __init__(self, factory: Callable[[], _Co_T] = ..., /): ...
    @property
    def is_locked(self) -> bool: ...
    def unlock(self): ...
    @abstractmethod
    def get_instance(self) -> _Co_T: ...

@final
class InjectableMode(str, Enum):
    FALLBACK = ...
    NORMAL = ...
    OVERRIDE = ...
