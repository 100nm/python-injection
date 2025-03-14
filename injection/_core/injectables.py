from abc import ABC, abstractmethod
from collections.abc import MutableMapping
from contextlib import suppress
from dataclasses import dataclass
from typing import (
    Any,
    AsyncContextManager,
    ClassVar,
    ContextManager,
    NoReturn,
    Protocol,
    runtime_checkable,
)

from injection._core.common.asynchronous import Caller
from injection._core.scope import Scope, get_active_scopes, get_scope
from injection.exceptions import InjectionError


@runtime_checkable
class Injectable[T](Protocol):
    __slots__ = ()

    @property
    def is_locked(self) -> bool:
        return False

    def unlock(self) -> None:
        return

    @abstractmethod
    async def aget_instance(self) -> T:
        raise NotImplementedError

    @abstractmethod
    def get_instance(self) -> T:
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class BaseInjectable[T](Injectable[T], ABC):
    factory: Caller[..., T]


class SimpleInjectable[T](BaseInjectable[T]):
    __slots__ = ()

    async def aget_instance(self) -> T:
        return await self.factory.acall()

    def get_instance(self) -> T:
        return self.factory.call()


class SingletonInjectable[T](BaseInjectable[T]):
    __slots__ = ("__dict__",)

    __key: ClassVar[str] = "$instance"

    @property
    def is_locked(self) -> bool:
        return self.__key in self.__cache

    @property
    def __cache(self) -> MutableMapping[str, Any]:
        return self.__dict__

    async def aget_instance(self) -> T:
        cache = self.__cache

        with suppress(KeyError):
            return cache[self.__key]

        instance = await self.factory.acall()
        cache[self.__key] = instance
        return instance

    def get_instance(self) -> T:
        cache = self.__cache

        with suppress(KeyError):
            return cache[self.__key]

        instance = self.factory.call()
        cache[self.__key] = instance
        return instance

    def unlock(self) -> None:
        self.__cache.pop(self.__key, None)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ScopedInjectable[R, T](Injectable[T], ABC):
    factory: Caller[..., R]
    scope_name: str

    @property
    def is_locked(self) -> bool:
        return any(self in scope.cache for scope in get_active_scopes(self.scope_name))

    @abstractmethod
    async def abuild(self, scope: Scope) -> T:
        raise NotImplementedError

    @abstractmethod
    def build(self, scope: Scope) -> T:
        raise NotImplementedError

    async def aget_instance(self) -> T:
        scope = self.get_scope()

        with suppress(KeyError):
            return scope.cache[self]

        instance = await self.abuild(scope)
        self.set_instance(instance, scope)
        return instance

    def get_instance(self) -> T:
        scope = self.get_scope()

        with suppress(KeyError):
            return scope.cache[self]

        instance = self.build(scope)
        self.set_instance(instance, scope)
        return instance

    def get_scope(self) -> Scope:
        return get_scope(self.scope_name)

    def set_instance(self, instance: T, scope: Scope) -> None:
        scope.cache[self] = instance

    def unlock(self) -> None:
        if self.is_locked:
            raise RuntimeError(f"To unlock, close the `{self.scope_name}` scope.")


class AsyncCMScopedInjectable[T](ScopedInjectable[AsyncContextManager[T], T]):
    __slots__ = ()

    async def abuild(self, scope: Scope) -> T:
        cm = await self.factory.acall()
        return await scope.aenter(cm)

    def build(self, scope: Scope) -> NoReturn:
        raise RuntimeError("Can't use async context manager synchronously.")


class CMScopedInjectable[T](ScopedInjectable[ContextManager[T], T]):
    __slots__ = ()

    async def abuild(self, scope: Scope) -> T:
        cm = await self.factory.acall()
        return scope.enter(cm)

    def build(self, scope: Scope) -> T:
        cm = self.factory.call()
        return scope.enter(cm)


class SimpleScopedInjectable[T](ScopedInjectable[T, T]):
    __slots__ = ()

    async def abuild(self, scope: Scope) -> T:
        return await self.factory.acall()

    def build(self, scope: Scope) -> T:
        return self.factory.call()

    def unlock(self) -> None:
        for scope in get_active_scopes(self.scope_name):
            scope.cache.pop(self, None)


@dataclass(repr=False, frozen=True, slots=True)
class ShouldBeInjectable[T](Injectable[T]):
    cls: type[T]

    async def aget_instance(self) -> T:
        return self.get_instance()

    def get_instance(self) -> NoReturn:
        raise InjectionError(f"`{self.cls}` should be an injectable.")
