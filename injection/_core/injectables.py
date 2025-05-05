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

from injection._core.common.asynchronous import Caller
from injection._core.common.asynchronous import (
    create_semaphore as _create_async_semaphore,
)
from injection._core.scope import (
    Scope,
    get_scope,
    in_scope_cache,
    remove_scoped_values,
)
from injection._core.slots import SlotKey
from injection.exceptions import EmptySlotError, InjectionError


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
class TransientInjectable[T](Injectable[T]):
    factory: Caller[..., T]

    async def aget_instance(self) -> T:
        return await self.factory.acall()

    def get_instance(self) -> T:
        return self.factory.call()


class CacheLogic[T]:
    __slots__ = ("__semaphore",)

    __semaphore: AsyncContextManager[Any]

    def __init__(self) -> None:
        self.__semaphore = _create_async_semaphore(1)

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


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SingletonInjectable[T](Injectable[T]):
    factory: Caller[..., T]
    cache: MutableMapping[str, T] = field(default_factory=dict)
    logic: CacheLogic[T] = field(default_factory=CacheLogic)

    __key: ClassVar[str] = "$instance"

    @property
    def is_locked(self) -> bool:
        return self.__key in self.cache

    async def aget_instance(self) -> T:
        return await self.logic.aget_or_create(
            self.cache,
            self.__key,
            self.factory.acall,
        )

    def get_instance(self) -> T:
        return self.logic.get_or_create(self.cache, self.__key, self.factory.call)

    def unlock(self) -> None:
        self.cache.pop(self.__key, None)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ScopedInjectable[R, T](Injectable[T], ABC):
    factory: Caller[..., R]
    scope_name: str
    logic: CacheLogic[T] = field(default_factory=CacheLogic)

    @property
    def is_locked(self) -> bool:
        return in_scope_cache(self, self.scope_name)

    @abstractmethod
    async def abuild(self, scope: Scope) -> T:
        raise NotImplementedError

    @abstractmethod
    def build(self, scope: Scope) -> T:
        raise NotImplementedError

    async def aget_instance(self) -> T:
        scope = self.__get_scope()
        factory = partial(self.abuild, scope)
        return await self.logic.aget_or_create(scope.cache, self, factory)

    def get_instance(self) -> T:
        scope = self.__get_scope()
        factory = partial(self.build, scope)
        return self.logic.get_or_create(scope.cache, self, factory)

    def unlock(self) -> None:
        if self.is_locked:
            raise RuntimeError(f"To unlock, close the `{self.scope_name}` scope.")

    def __get_scope(self) -> Scope:
        return get_scope(self.scope_name)


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
        remove_scoped_values(self, self.scope_name)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ScopedSlotInjectable[T](Injectable[T]):
    cls: type[T]
    scope_name: str
    key: SlotKey[T] = field(default_factory=SlotKey)

    @property
    def is_locked(self) -> bool:
        return in_scope_cache(self.key, self.scope_name)

    async def aget_instance(self) -> T:
        return self.get_instance()

    def get_instance(self) -> T:
        scope_name = self.scope_name
        scope = get_scope(scope_name)

        try:
            return scope.cache[self.key]
        except KeyError as exc:
            raise EmptySlotError(
                f"The slot for `{self.cls}` isn't set in the current `{scope_name}` scope."
            ) from exc

    def unlock(self) -> None:
        remove_scoped_values(self.key, self.scope_name)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ShouldBeInjectable[T](Injectable[T]):
    cls: type[T]

    async def aget_instance(self) -> T:
        return self.get_instance()

    def get_instance(self) -> NoReturn:
        raise InjectionError(f"`{self.cls}` should be an injectable.")
