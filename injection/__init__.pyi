from abc import abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping
from contextlib import asynccontextmanager, contextmanager
from enum import Enum
from logging import Logger
from typing import Any, Final, Protocol, Self, final, overload, runtime_checkable

from ._core.asfunction import AsFunctionWrappedType as _AsFunctionWrappedType
from ._core.common.invertible import Invertible as _Invertible
from ._core.common.type import InputType as _InputType
from ._core.common.type import TypeInfo as _TypeInfo
from ._core.locator import InjectableFactory as _InjectableFactory
from ._core.locator import ModeStr
from ._core.module import PriorityStr
from ._core.scope import ScopeKindStr

class _Decorator(Protocol):
    def __call__[T](self, wrapped: T, /) -> T: ...

_default_module: Final[Module] = ...

afind_instance = _default_module.afind_instance
aget_instance = _default_module.aget_instance
aget_lazy_instance = _default_module.aget_lazy_instance
constant = _default_module.constant
find_instance = _default_module.find_instance
get_instance = _default_module.get_instance
get_lazy_instance = _default_module.get_lazy_instance
inject = _default_module.inject
injectable = _default_module.injectable
reserve_scoped_slot = _default_module.reserve_scoped_slot
scoped = _default_module.scoped
set_constant = _default_module.set_constant
should_be_injectable = _default_module.should_be_injectable
singleton = _default_module.singleton

@overload
def asfunction[**P, T](
    wrapped: _AsFunctionWrappedType[P, T],
    /,
    *,
    module: Module = ...,
    threadsafe: bool | None = ...,
) -> Callable[P, T]: ...
@overload
def asfunction[**P, T](
    wrapped: None = ...,
    /,
    *,
    module: Module = ...,
    threadsafe: bool | None = ...,
) -> Callable[[_AsFunctionWrappedType[P, T]], Callable[P, T]]: ...
@asynccontextmanager
def adefine_scope(
    name: str,
    /,
    kind: ScopeKind | ScopeKindStr = ...,
    threadsafe: bool | None = ...,
) -> AsyncIterator[Scope]: ...
@contextmanager
def define_scope(
    name: str,
    /,
    kind: ScopeKind | ScopeKindStr = ...,
    threadsafe: bool | None = ...,
) -> Iterator[Scope]: ...
def mod(name: str = ..., /) -> Module:
    """
    Short syntax for `Module.from_name`.
    """
@runtime_checkable
class Injectable[T](Protocol):
    @property
    def is_locked(self) -> bool: ...
    def unlock(self) -> None: ...
    @abstractmethod
    async def aget_instance(self) -> T: ...
    @abstractmethod
    def get_instance(self) -> T: ...

@final
class ScopeKind(Enum):
    CONTEXTUAL = ...
    SHARED = ...

@runtime_checkable
class Scope(Protocol):
    @abstractmethod
    def set_slot[T](self, key: SlotKey[T], value: T) -> Self: ...
    @abstractmethod
    def slot_map(self, mapping: Mapping[SlotKey[Any], Any], /) -> Self: ...

class SlotKey[T]: ...

class MappedScope:
    def __init__(self, name: str, /, module: Module = ...) -> None: ...
    @overload
    def __get__(
        self,
        instance: object,
        owner: type | None = ...,
    ) -> _BoundMappedScope: ...
    @overload
    def __get__(self, instance: None = ..., owner: type | None = ...) -> Self: ...
    def __set_name__(self, owner: type, name: str) -> None: ...

class _BoundMappedScope:
    @asynccontextmanager
    def adefine(
        self,
        /,
        kind: ScopeKind | ScopeKindStr = ...,
        threadsafe: bool | None = ...,
    ) -> AsyncIterator[None]: ...
    @contextmanager
    def define(
        self,
        /,
        kind: ScopeKind | ScopeKindStr = ...,
        threadsafe: bool | None = ...,
    ) -> Iterator[None]: ...

class LazyInstance[T]:
    def __init__(
        self,
        cls: _InputType[T],
        /,
        default: T = ...,
        *,
        module: Module = ...,
        threadsafe: bool | None = ...,
    ) -> None: ...
    @overload
    def __get__(self, instance: object, owner: type | None = ...) -> T: ...
    @overload
    def __get__(self, instance: None = ..., owner: type | None = ...) -> Self: ...

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
    @overload
    def inject[T](
        self,
        wrapped: T,
        /,
        *,
        threadsafe: bool | None = ...,
    ) -> T:
        """
        Decorator applicable to a class or function. Inject function dependencies using
        parameter type annotations. If applied to a class, the dependencies resolved
        will be those of the `__init__` method.

        With `threadsafe=True`, the injection logic is wrapped in a `threading.RLock`.
        """

    @overload
    def inject(
        self,
        wrapped: None = ...,
        /,
        *,
        threadsafe: bool | None = ...,
    ) -> _Decorator: ...
    @overload
    def injectable[T](
        self,
        wrapped: T,
        /,
        *,
        cls: _InjectableFactory[Any] = ...,
        ignore_type_hint: bool = ...,
        inject: bool = ...,
        on: _TypeInfo[Any] = ...,
        mode: Mode | ModeStr = ...,
    ) -> T:
        """
        Decorator applicable to a class or function. It is used to indicate how the
        injectable will be constructed. At injection time, a new instance will be
        injected each time.
        """

    @overload
    def injectable(
        self,
        wrapped: None = ...,
        /,
        *,
        cls: _InjectableFactory[Any] = ...,
        ignore_type_hint: bool = ...,
        inject: bool = ...,
        on: _TypeInfo[Any] = ...,
        mode: Mode | ModeStr = ...,
    ) -> _Decorator: ...
    @overload
    def singleton[T](
        self,
        wrapped: T,
        /,
        *,
        ignore_type_hint: bool = ...,
        inject: bool = ...,
        on: _TypeInfo[Any] = ...,
        mode: Mode | ModeStr = ...,
    ) -> T:
        """
        Decorator applicable to a class or function. It is used to indicate how the
        singleton will be constructed. At injection time, the injected instance will
        always be the same.
        """

    @overload
    def singleton(
        self,
        wrapped: None = ...,
        /,
        *,
        ignore_type_hint: bool = ...,
        inject: bool = ...,
        on: _TypeInfo[Any] = ...,
        mode: Mode | ModeStr = ...,
    ) -> _Decorator: ...
    def scoped(
        self,
        scope_name: str,
        /,
        *,
        ignore_type_hint: bool = ...,
        inject: bool = ...,
        on: _TypeInfo[Any] = ...,
        mode: Mode | ModeStr = ...,
    ) -> _Decorator:
        """
        Decorator applicable to a class or function or generator function. It is used
        to indicate how the scoped instance will be constructed. At injection time, the
        injected instance is retrieved from the scope.
        """

    @overload
    def should_be_injectable[T](self, wrapped: T, /) -> T:
        """
        Decorator applicable to a class. It is used to specify whether an injectable
        should be registered. Raise an exception at injection time if the class isn't
        registered.
        """

    @overload
    def should_be_injectable(
        self,
        wrapped: None = ...,
        /,
    ) -> _Decorator: ...
    @overload
    def constant[T](
        self,
        wrapped: T,
        /,
        *,
        ignore_type_hint: bool = ...,
        on: _TypeInfo[Any] = ...,
        mode: Mode | ModeStr = ...,
    ) -> T:
        """
        Decorator applicable to a class or function. It is used to indicate how the
        constant is constructed. At injection time, the injected instance will always
        be the same. Unlike `@singleton`, dependencies will not be resolved.
        """

    @overload
    def constant(
        self,
        wrapped: None = ...,
        /,
        *,
        ignore_type_hint: bool = ...,
        on: _TypeInfo[Any] = ...,
        mode: Mode | ModeStr = ...,
    ) -> _Decorator: ...
    def set_constant[T](
        self,
        instance: T,
        on: _TypeInfo[Any] = ...,
        *,
        alias: bool = ...,
        mode: Mode | ModeStr = ...,
    ) -> T:
        """
        Function for registering a specific instance to be injected. This is useful for
        registering global variables. The difference with the singleton decorator is
        that no dependencies are resolved, so the module doesn't need to be locked.
        """

    def reserve_scoped_slot[T](
        self,
        cls: _InputType[T],
        /,
        scope_name: str,
        *,
        mode: Mode | ModeStr = ...,
    ) -> SlotKey[T]: ...
    def make_injected_function[**P, T](
        self,
        wrapped: Callable[P, T],
        /,
        threadsafe: bool | None = ...,
    ) -> Callable[P, T]: ...
    def make_async_factory[T](
        self,
        wrapped: type[T],
        /,
        threadsafe: bool | None = ...,
    ) -> Callable[..., Awaitable[T]]: ...
    async def afind_instance[T](
        self,
        cls: _InputType[T],
        *,
        threadsafe: bool | None = ...,
    ) -> T: ...
    def find_instance[T](
        self,
        cls: _InputType[T],
        *,
        threadsafe: bool | None = ...,
    ) -> T:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or an exception will be raised.
        """

    @overload
    async def aget_instance[T, Default](
        self,
        cls: _InputType[T],
        default: Default,
        *,
        threadsafe: bool | None = ...,
    ) -> T | Default: ...
    @overload
    async def aget_instance[T](
        self,
        cls: _InputType[T],
        default: T = ...,
        *,
        threadsafe: bool | None = ...,
    ) -> T: ...
    @overload
    def get_instance[T, Default](
        self,
        cls: _InputType[T],
        default: Default,
        *,
        threadsafe: bool | None = ...,
    ) -> T | Default:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or return `NotImplemented`.
        """

    @overload
    def get_instance[T](
        self,
        cls: _InputType[T],
        default: T = ...,
        *,
        threadsafe: bool | None = ...,
    ) -> T: ...
    @overload
    def aget_lazy_instance[T, Default](
        self,
        cls: _InputType[T],
        default: Default,
        *,
        threadsafe: bool | None = ...,
    ) -> Awaitable[T | Default]: ...
    @overload
    def aget_lazy_instance[T](
        self,
        cls: _InputType[T],
        default: T = ...,
        *,
        threadsafe: bool | None = ...,
    ) -> Awaitable[T]: ...
    @overload
    def get_lazy_instance[T, Default](
        self,
        cls: _InputType[T],
        default: Default,
        *,
        threadsafe: bool | None = ...,
    ) -> _Invertible[T | Default]:
        """
        Function used to retrieve an instance associated with the type passed in
        parameter or `NotImplemented`. Return an `Invertible` object. To access the
        instance contained in an invertible object, simply use a wavy line (~).

        Example: instance = ~lazy_instance
        """

    @overload
    def get_lazy_instance[T](
        self,
        cls: _InputType[T],
        default: T = ...,
        *,
        threadsafe: bool | None = ...,
    ) -> _Invertible[T]: ...
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

    @contextmanager
    def use_temporarily(
        self,
        module: Module,
        *,
        priority: Priority | PriorityStr = ...,
        unlock: bool = ...,
    ) -> Iterator[Self]:
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

    async def all_ready(self) -> None: ...
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
class Mode(Enum):
    FALLBACK = ...
    NORMAL = ...
    OVERRIDE = ...

@final
class Priority(Enum):
    LOW = ...
    HIGH = ...
