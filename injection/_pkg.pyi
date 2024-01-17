from abc import abstractmethod
from collections.abc import Callable, Iterable
from contextlib import ContextDecorator
from enum import Enum
from types import UnionType
from typing import (
    Any,
    ContextManager,
    Final,
    Protocol,
    TypeVar,
    final,
    runtime_checkable,
)

from injection.common.lazy import Lazy

_T = TypeVar("_T")

default_module: Final[Module] = ...

get_instance = default_module.get_instance
get_lazy_instance = default_module.get_lazy_instance
inject = default_module.inject
injectable = default_module.injectable
set_constant = default_module.set_constant
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
        on: type | Iterable[type] | UnionType = ...,
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
        on: type | Iterable[type] | UnionType = ...,
    ):
        """
        Decorator applicable to a class or function. It is used to indicate how the
        singleton will be constructed. At injection time, the injected instance will
        always be the same.
        """
    def set_constant(
        self,
        instance: _T,
        on: type | Iterable[type] | UnionType = ...,
    ) -> _T:
        """
        Function for registering a specific instance to be injected. This is useful for
        registering global variables. The difference with the singleton decorator is
        that no dependencies are resolved, so the module doesn't need to be locked.
        """
    def get_instance(self, cls: type[_T]) -> _T | None:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or return `None`.
        """
    def get_lazy_instance(self, cls: type[_T]) -> Lazy[_T | None]:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or `None`. Return a `Lazy` object. To access the instance contained
        in a lazy object, simply use a wavy line (~).

        Example: instance = ~lazy_instance
        """
    def use(self, module: Module, priority: ModulePriorities = ...):
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
        priority: ModulePriorities = ...,
    ) -> ContextManager | ContextDecorator:
        """
        Context manager or decorator for temporary use of a module.
        """
    def change_priority(self, module: Module, priority: ModulePriorities):
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
class ModulePriorities(Enum):
    HIGH = ...
    LOW = ...

@runtime_checkable
class Injectable(Protocol[_T]):
    def __init__(self, factory: Callable[[], _T] = ..., *args, **kwargs): ...
    @property
    def is_locked(self) -> bool: ...
    def unlock(self): ...
    @abstractmethod
    def get_instance(self) -> _T: ...
