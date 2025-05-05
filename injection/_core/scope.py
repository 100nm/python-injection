from __future__ import annotations

import itertools
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import AsyncIterator, Iterator, Mapping, MutableMapping
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import StrEnum
from types import EllipsisType, TracebackType
from typing import (
    Any,
    AsyncContextManager,
    ContextManager,
    Final,
    Literal,
    NoReturn,
    Protocol,
    Self,
    overload,
    runtime_checkable,
)

from injection._core.common.key import new_short_key
from injection._core.slots import SlotKey
from injection.exceptions import (
    InjectionError,
    ScopeAlreadyDefinedError,
    ScopeError,
    ScopeUndefinedError,
)


class ScopeKind(StrEnum):
    CONTEXTUAL = "contextual"
    SHARED = "shared"

    @classmethod
    def get_default(cls) -> ScopeKind:
        return cls.CONTEXTUAL


type ScopeKindStr = Literal["contextual", "shared"]


@runtime_checkable
class ScopeState(Protocol):
    __slots__ = ()

    @property
    @abstractmethod
    def active_scopes(self) -> Iterator[Scope]:
        raise NotImplementedError

    @abstractmethod
    def bind(self, scope: Scope) -> ContextManager[None]:
        raise NotImplementedError

    @abstractmethod
    def get_scope(self) -> Scope | None:
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class _ContextualScopeState(ScopeState):
    # Shouldn't be instantiated outside `__CONTEXTUAL_SCOPES`.

    __context_var: ContextVar[Scope] = field(
        default_factory=lambda: ContextVar(f"scope@{new_short_key()}"),
        init=False,
    )
    __references: set[Scope] = field(
        default_factory=set,
        init=False,
    )

    @property
    def active_scopes(self) -> Iterator[Scope]:
        return iter(self.__references)

    @contextmanager
    def bind(self, scope: Scope) -> Iterator[None]:
        self.__references.add(scope)
        token = self.__context_var.set(scope)

        try:
            yield
        finally:
            self.__context_var.reset(token)
            self.__references.remove(scope)

    def get_scope(self) -> Scope | None:
        return self.__context_var.get(None)


@dataclass(repr=False, slots=True)
class _SharedScopeState(ScopeState):
    __scope: Scope | None = field(default=None)

    @property
    def active_scopes(self) -> Iterator[Scope]:
        if scope := self.__scope:
            yield scope

    @contextmanager
    def bind(self, scope: Scope) -> Iterator[None]:
        self.__scope = scope

        try:
            yield
        finally:
            self.__scope = None

    def get_scope(self) -> Scope | None:
        return self.__scope


__CONTEXTUAL_SCOPES: Final[Mapping[str, ScopeState]] = defaultdict(
    _ContextualScopeState,
)
__SHARED_SCOPES: Final[Mapping[str, ScopeState]] = defaultdict(
    _SharedScopeState,
)


@asynccontextmanager
async def adefine_scope(
    name: str,
    /,
    kind: ScopeKind | ScopeKindStr = ScopeKind.get_default(),
) -> AsyncIterator[ScopeFacade]:
    async with AsyncScope() as scope:
        with _bind_scope(name, scope, kind) as facade:
            yield facade


@contextmanager
def define_scope(
    name: str,
    /,
    kind: ScopeKind | ScopeKindStr = ScopeKind.get_default(),
) -> Iterator[ScopeFacade]:
    with SyncScope() as scope:
        with _bind_scope(name, scope, kind) as facade:
            yield facade


def get_active_scopes(name: str) -> tuple[Scope, ...]:
    active_scopes = (
        state.active_scopes
        for states in (__CONTEXTUAL_SCOPES, __SHARED_SCOPES)
        if (state := states.get(name))
    )
    return tuple(itertools.chain.from_iterable(active_scopes))


@overload
def get_scope(name: str, default: EllipsisType = ...) -> Scope: ...


@overload
def get_scope[T](name: str, default: T) -> Scope | T: ...


def get_scope[T](name: str, default: T | EllipsisType = ...) -> Scope | T:
    for states in (__CONTEXTUAL_SCOPES, __SHARED_SCOPES):
        state = states.get(name)
        if state and (scope := state.get_scope()):
            return scope

    if default is Ellipsis:
        raise ScopeUndefinedError(
            f"Scope `{name}` isn't defined in the current context."
        )

    return default


def in_scope_cache(key: Any, scope_name: str) -> bool:
    return any(key in scope.cache for scope in get_active_scopes(scope_name))


def remove_scoped_values(key: Any, scope_name: str) -> None:
    for scope in get_active_scopes(scope_name):
        scope.cache.pop(key, None)


@contextmanager
def _bind_scope(
    name: str,
    scope: Scope,
    kind: ScopeKind | ScopeKindStr,
) -> Iterator[ScopeFacade]:
    match ScopeKind(kind):
        case ScopeKind.CONTEXTUAL:
            is_already_defined = bool(get_scope(name, default=None))
            states = __CONTEXTUAL_SCOPES

        case ScopeKind.SHARED:
            is_already_defined = bool(get_active_scopes(name))
            states = __SHARED_SCOPES

        case _:
            raise NotImplementedError

    if is_already_defined:
        raise ScopeAlreadyDefinedError(
            f"Scope `{name}` is already defined in the current context."
        )

    with states[name].bind(scope):
        yield _UserScope(scope)


@runtime_checkable
class Scope(Protocol):
    __slots__ = ()

    cache: MutableMapping[Any, Any]

    @abstractmethod
    async def aenter[T](self, context_manager: AsyncContextManager[T]) -> T:
        raise NotImplementedError

    @abstractmethod
    def enter[T](self, context_manager: ContextManager[T]) -> T:
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class BaseScope[T](Scope, ABC):
    delegate: T
    cache: MutableMapping[Any, Any] = field(
        default_factory=dict,
        init=False,
        hash=False,
    )


class AsyncScope(BaseScope[AsyncExitStack]):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__(delegate=AsyncExitStack())

    async def __aenter__(self) -> Self:
        await self.delegate.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Any:
        return await self.delegate.__aexit__(exc_type, exc_value, traceback)

    async def aenter[T](self, context_manager: AsyncContextManager[T]) -> T:
        return await self.delegate.enter_async_context(context_manager)

    def enter[T](self, context_manager: ContextManager[T]) -> T:
        return self.delegate.enter_context(context_manager)


class SyncScope(BaseScope[ExitStack]):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__(delegate=ExitStack())

    def __enter__(self) -> Self:
        self.delegate.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Any:
        return self.delegate.__exit__(exc_type, exc_value, traceback)

    async def aenter[T](self, context_manager: AsyncContextManager[T]) -> NoReturn:
        raise ScopeError("Synchronous scope doesn't support async context manager.")

    def enter[T](self, context_manager: ContextManager[T]) -> T:
        return self.delegate.enter_context(context_manager)


@runtime_checkable
class ScopeFacade(Protocol):
    __slots__ = ()

    @abstractmethod
    def set_slot[T](self, key: SlotKey[T], value: T) -> Self:
        raise NotImplementedError

    @abstractmethod
    def slot_map(self, mapping: Mapping[SlotKey[Any], Any], /) -> Self:
        raise NotImplementedError


@dataclass(repr=False, frozen=True, slots=True)
class _UserScope(ScopeFacade):
    scope: Scope

    def set_slot[T](self, key: SlotKey[T], value: T) -> Self:
        return self.slot_map({key: value})

    def slot_map(self, mapping: Mapping[SlotKey[Any], Any], /) -> Self:
        cache = self.scope.cache

        for slot_key in mapping:
            if slot_key in cache:
                raise InjectionError("Slot already set.")

        cache.update(mapping)
        return self
