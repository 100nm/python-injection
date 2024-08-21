from abc import abstractmethod
from collections.abc import Callable
from contextlib import ContextDecorator
from enum import Enum
from logging import Logger
from typing import (
    Any,
    ContextManager,
    Protocol,
    Self,
    final,
    runtime_checkable,
)

from ._core.common.invertible import Invertible as _Invertible
from ._core.common.type import InputType as _InputType
from ._core.common.type import TypeInfo as _TypeInfo
from ._core.module import InjectableFactory as _InjectableFactory
from ._core.module import ModeStr, PriorityStr

_: Module = ...

constant = _.constant
find_instance = _.find_instance
get_instance = _.get_instance
get_lazy_instance = _.get_lazy_instance
inject = _.inject
injectable = _.injectable
set_constant = _.set_constant
should_be_injectable = _.should_be_injectable
singleton = _.singleton

del _

def mod(name: str = ..., /) -> Module:
    """
    Short syntax for `Module.from_name`.
    """
@final
class Module:
    """
    Object with isolated injection environment.

    Modules have been designed to simplify unit test writing. So think carefully before
    instantiating a new one. They could increase complexity unnecessarily if used
    extensively.
    """

    name: str

    def __init__(self, name: str = ...) -> None: ...
    def __contains__(self, cls: _InputType[Any], /) -> bool: ...
    @property
    def is_locked(self) -> bool: ...
    def inject[**P, T](self, wrapped: Callable[P, T] = ..., /):  # type: ignore[no-untyped-def]
        """
        Decorator applicable to a class or function. Inject function dependencies using
        parameter type annotations. If applied to a class, the dependencies resolved
        will be those of the `__init__` method.
        """

    def injectable[**P, T](  # type: ignore[no-untyped-def]
        self,
        wrapped: Callable[P, T] = ...,
        /,
        *,
        cls: _InjectableFactory[T] = ...,
        inject: bool = ...,
        on: _TypeInfo[T] = ...,
        mode: Mode | ModeStr = ...,
    ):
        """
        Decorator applicable to a class or function. It is used to indicate how the
        injectable will be constructed. At injection time, a new instance will be
        injected each time.
        """

    def singleton[**P, T](  # type: ignore[no-untyped-def]
        self,
        wrapped: Callable[P, T] = ...,
        /,
        *,
        inject: bool = ...,
        on: _TypeInfo[T] = ...,
        mode: Mode | ModeStr = ...,
    ):
        """
        Decorator applicable to a class or function. It is used to indicate how the
        singleton will be constructed. At injection time, the injected instance will
        always be the same.
        """

    def should_be_injectable[T](self, wrapped: type[T] = ..., /):  # type: ignore[no-untyped-def]
        """
        Decorator applicable to a class. It is used to specify whether an injectable
        should be registered. Raise an exception at injection time if the class isn't
        registered.
        """

    def constant[**P, T](  # type: ignore[no-untyped-def]
        self,
        wrapped: Callable[P, T] = ...,
        /,
        *,
        on: _TypeInfo[T] = ...,
        mode: Mode | ModeStr = ...,
    ):
        """
        Decorator applicable to a class or function. It is used to indicate how the
        constant is constructed. At injection time, the injected instance will always
        be the same. Unlike `@singleton`, dependencies will not be resolved.
        """

    def set_constant[T](
        self,
        instance: T,
        on: _TypeInfo[T] = ...,
        *,
        alias: bool = ...,
        mode: Mode | ModeStr = ...,
    ) -> Self:
        """
        Function for registering a specific instance to be injected. This is useful for
        registering global variables. The difference with the singleton decorator is
        that no dependencies are resolved, so the module doesn't need to be locked.
        """

    def find_instance[T](self, cls: _InputType[T]) -> T:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or an exception will be raised.
        """

    def get_instance[T](self, cls: _InputType[T]) -> T | None:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or return `None`.
        """

    def get_lazy_instance[T](
        self,
        cls: _InputType[T],
        *,
        cache: bool = ...,
    ) -> _Invertible[T | None]:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or `None`. Return a `Invertible` object. To access the instance
        contained in an invertible object, simply use a wavy line (~).
        With `cache=True`, the instance retrieved will always be the same.

        Example: instance = ~lazy_instance
        """

    def init_modules(self, *modules: Module) -> Self:
        """
        Function to clean modules in use and to use those passed as parameters.
        """

    def use(
        self,
        module: Module,
        *,
        priority: Priority | PriorityStr = ...,
    ) -> Self:
        """
        Function for using another module. Using another module replaces the module's
        dependencies with those of the module used. If the dependency is not found, it
        will be searched for in the module's dependency container.
        """

    def stop_using(self, module: Module) -> Self:
        """
        Function to remove a module in use.
        """

    def use_temporarily(
        self,
        module: Module,
        *,
        priority: Priority | PriorityStr = ...,
    ) -> ContextManager[None] | ContextDecorator:
        """
        Context manager or decorator for temporary use of a module.
        """

    def change_priority(
        self,
        module: Module,
        priority: Priority | PriorityStr,
    ) -> Self:
        """
        Function for changing the priority of a module in use.
        There are two priority values:

        * **LOW**: The module concerned becomes the least important of the modules used.
        * **HIGH**: The module concerned becomes the most important of the modules used.
        """

    def unlock(self) -> Self:
        """
        Function to unlock the module by deleting cached instances of singletons.
        """

    def add_logger(self, logger: Logger) -> Self: ...
    @classmethod
    def from_name(cls, name: str) -> Module:
        """
        Class method for getting or creating a module by name.
        """

    @classmethod
    def default(cls) -> Module:
        """
        Class method for getting the default module.
        """

@final
class Priority(Enum):
    LOW = ...
    HIGH = ...

@runtime_checkable
class Injectable[T](Protocol):
    @property
    def is_locked(self) -> bool: ...
    def unlock(self) -> None: ...
    @abstractmethod
    def get_instance(self) -> T: ...

@final
class Mode(Enum):
    FALLBACK = ...
    NORMAL = ...
    OVERRIDE = ...
