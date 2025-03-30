from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import suppress
from dataclasses import dataclass, field
from functools import partial
from typing import (
    Any,
    AsyncContextManager,
    ClassVar,
    ContextManager,
    NoReturn,
    Protocol,
    runtime_checkable,
)

from injection._core.common.asynchronous import Caller, create_semaphore
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


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class BaseInjectable[R, T](Injectable[T], ABC):
    factory: Caller[..., R]


class SimpleInjectable[T](BaseInjectable[T, T]):
    __slots__ = ()

    async def aget_instance(self) -> T:
        return await self.factory.acall()

    def get_instance(self) -> T:
        return self.factory.call()


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class CachedInjectable[R, T](BaseInjectable[R, T], ABC):
    __semaphore: AsyncContextManager[Any] = field(
        default_factory=partial(create_semaphore, 1),
        init=False,
        hash=False,
    )

    async def aget_or_create[K](
        self,
        cache: MutableMapping[K, T],
        key: K,
        factory: Callable[..., Awaitable[T]],
    ) -> T:
        async with self.__semaphore:
            with suppress(KeyError):
                return cache[key]

            instance = await factory()
            cache[key] = instance

        return instance

    def get_or_create[K](
        self,
        cache: MutableMapping[K, T],
        key: K,
        factory: Callable[..., T],
    ) -> T:
        with suppress(KeyError):
            return cache[key]

        instance = factory()
        cache[key] = instance
        return instance


class SingletonInjectable[T](CachedInjectable[T, T]):
    __slots__ = ("__dict__",)

    __key: ClassVar[str] = "$instance"

    @property
    def is_locked(self) -> bool:
        return self.__key in self.__cache

    @property
    def __cache(self) -> MutableMapping[str, Any]:
        return self.__dict__

    async def aget_instance(self) -> T:
        return await self.aget_or_create(self.__cache, self.__key, self.factory.acall)

    def get_instance(self) -> T:
        return self.get_or_create(self.__cache, self.__key, self.factory.call)

    def unlock(self) -> None:
        self.__cache.pop(self.__key, None)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ScopedInjectable[R, T](CachedInjectable[R, T], ABC):
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
        factory = partial(self.abuild, scope)
        return await self.aget_or_create(scope.cache, self, factory)

    def get_instance(self) -> T:
        scope = self.get_scope()
        factory = partial(self.build, scope)
        return self.get_or_create(scope.cache, self, factory)

    def get_scope(self) -> Scope:
        return get_scope(self.scope_name)

    def setdefault(self, instance: T) -> T:
        scope = self.get_scope()
        return self.get_or_create(scope.cache, self, lambda: instance)

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


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ShouldBeInjectable[T](Injectable[T]):
    cls: type[T]

    async def aget_instance(self) -> T:
        return self.get_instance()

    def get_instance(self) -> NoReturn:
        raise InjectionError(f"`{self.cls}` should be an injectable.")
