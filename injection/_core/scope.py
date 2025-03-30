from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import AsyncIterator, Iterator, MutableMapping
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from types import TracebackType
from typing import (
    Any,
    AsyncContextManager,
    ContextManager,
    Final,
    NoReturn,
    Protocol,
    Self,
    runtime_checkable,
)

from injection._core.common.key import new_short_key
from injection.exceptions import (
    ScopeAlreadyDefinedError,
    ScopeError,
    ScopeUndefinedError,
)


@dataclass(repr=False, slots=True)
class _ScopeState:
    # Shouldn't be instantiated outside `__SCOPES`.

    __context_var: ContextVar[Scope] = field(
        default_factory=lambda: ContextVar(f"scope@{new_short_key()}"),
        init=False,
    )
    __default: Scope | None = field(
        default=None,
        init=False,
    )
    __references: set[Scope] = field(
        default_factory=set,
        init=False,
    )

    @property
    def active_scopes(self) -> Iterator[Scope]:
        yield from self.__references

        if default := self.__default:
            yield default

    @contextmanager
    def bind_contextual_scope(self, scope: Scope) -> Iterator[None]:
        self.__references.add(scope)
        token = self.__context_var.set(scope)

        try:
            yield
        finally:
            self.__context_var.reset(token)
            self.__references.remove(scope)

    @contextmanager
    def bind_shared_scope(self, scope: Scope) -> Iterator[None]:
        if next(self.active_scopes, None):
            raise ScopeError(
                "A shared scope can't be defined when one or more contextual scopes "
                "are defined on the same name."
            )

        self.__default = scope

        try:
            yield
        finally:
            self.__default = None

    def get_scope(self) -> Scope | None:
        return self.__context_var.get(self.__default)


__SCOPES: Final[defaultdict[str, _ScopeState]] = defaultdict(_ScopeState)


@asynccontextmanager
async def adefine_scope(name: str, *, shared: bool = False) -> AsyncIterator[None]:
    async with AsyncScope() as scope:
        scope.enter(_bind_scope(name, scope, shared))
        yield


@contextmanager
def define_scope(name: str, *, shared: bool = False) -> Iterator[None]:
    with SyncScope() as scope:
        scope.enter(_bind_scope(name, scope, shared))
        yield


def get_active_scopes(name: str) -> tuple[Scope, ...]:
    state = __SCOPES.get(name)

    if state is None:
        return ()

    return tuple(state.active_scopes)


def get_scope(name: str) -> Scope:
    state = __SCOPES.get(name)

    if state is None or (scope := state.get_scope()) is None:
        raise ScopeUndefinedError(
            f"Scope `{name}` isn't defined in the current context."
        )

    return scope


@contextmanager
def _bind_scope(name: str, scope: Scope, shared: bool) -> Iterator[None]:
    state = __SCOPES[name]

    if state.get_scope():
        raise ScopeAlreadyDefinedError(
            f"Scope `{name}` is already defined in the current context."
        )

    strategy = state.bind_shared_scope if shared else state.bind_contextual_scope
    with strategy(scope):
        yield


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
