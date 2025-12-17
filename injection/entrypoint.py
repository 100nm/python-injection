from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Coroutine, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from types import ModuleType as PythonModule
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Protocol,
    Self,
    overload,
    runtime_checkable,
)

from injection import Module
from injection.loaders import ProfileLoader, PythonModuleLoader

__all__ = ("AsyncEntrypoint", "Entrypoint", "entrypointmaker")

type Entrypoint[**P, T] = EntrypointBuilder[P, Any, T]
type AsyncEntrypoint[**P, T] = Entrypoint[P, Awaitable[T]]

type EntrypointSetupMethod[**P, **EPP, T1, T2] = Callable[
    Concatenate[Entrypoint[EPP, T1], P],
    Entrypoint[EPP, T2],
]


class Rule[**P, T1, T2](ABC):
    __slots__ = ()

    @abstractmethod
    def apply(self, wrapped: Callable[P, T1]) -> Callable[P, T2]:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _AsyncToSyncRule[**P, T](Rule[P, Awaitable[T], T]):
    run: Callable[[Awaitable[T]], T]

    def apply(self, wrapped: Callable[P, Awaitable[T]]) -> Callable[P, T]:
        @wraps(wrapped)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return self.run(wrapped(*args, **kwargs))

        return wrapper


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _DecorateRule[**P, T1, T2](Rule[P, T1, T2]):
    decorator: Callable[[Callable[P, T1]], Callable[P, T2]]

    def apply(self, wrapped: Callable[P, T1]) -> Callable[P, T2]:
        return self.decorator(wrapped)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _InjectRule[**P, T](Rule[P, T, T]):
    module: Module

    def apply(self, wrapped: Callable[P, T]) -> Callable[P, T]:
        return self.module.make_injected_function(wrapped)


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _LoadModulesRule[**P, T](Rule[P, T, T]):
    loader: PythonModuleLoader
    packages: Sequence[PythonModule | str]

    def apply(self, wrapped: Callable[P, T]) -> Callable[P, T]:
        return self.__decorator()(wrapped)

    @contextmanager
    def __decorator(self) -> Iterator[None]:
        self.loader.load(*self.packages)
        yield


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _LoadProfileRule[**P, T](Rule[P, T, T]):
    loader: ProfileLoader
    profile_name: str

    def apply(self, wrapped: Callable[P, T]) -> Callable[P, T]:
        return self.__decorator()(wrapped)

    @contextmanager
    def __decorator(self) -> Iterator[None]:
        with self.loader.load(self.profile_name):
            yield


@runtime_checkable
class _EntrypointDecorator[**P, T1, T2](Protocol):
    __slots__ = ()

    if TYPE_CHECKING:  # pragma: no cover

        @overload
        def __call__(
            self,
            wrapped: Callable[P, T1],
            /,
            *,
            autocall: bool = ...,
        ) -> Callable[P, T2]: ...

        @overload
        def __call__(
            self,
            wrapped: None = ...,
            /,
            *,
            autocall: bool = ...,
        ) -> Callable[[Callable[P, T1]], Callable[P, T2]]: ...

    @abstractmethod
    def __call__(
        self,
        wrapped: Callable[P, T1] | None = ...,
        /,
        *,
        autocall: bool = ...,
    ) -> Any:
        raise NotImplementedError


# SMP = Setup Method Parameters
# EPP = EntryPoint Parameters


if TYPE_CHECKING:  # pragma: no cover

    @overload
    def entrypointmaker[**SMP, **EPP, T1, T2](
        wrapped: EntrypointSetupMethod[SMP, EPP, T1, T2],
        /,
        *,
        profile_loader: ProfileLoader = ...,
    ) -> _EntrypointDecorator[EPP, T1, T2]: ...

    @overload
    def entrypointmaker[**SMP, **EPP, T1, T2](
        wrapped: None = ...,
        /,
        *,
        profile_loader: ProfileLoader = ...,
    ) -> Callable[
        [EntrypointSetupMethod[SMP, EPP, T1, T2]],
        _EntrypointDecorator[EPP, T1, T2],
    ]: ...


def entrypointmaker[**SMP, **EPP, T1, T2](
    wrapped: EntrypointSetupMethod[SMP, EPP, T1, T2] | None = None,
    /,
    *,
    profile_loader: ProfileLoader | None = None,
) -> Any:
    def decorator(
        wp: EntrypointSetupMethod[SMP, EPP, T1, T2],
    ) -> _EntrypointDecorator[EPP, T1, T2]:
        pl = (profile_loader or ProfileLoader()).init()
        setup_method = pl.module.make_injected_function(wp)
        return setup_method(EntrypointBuilder(pl))  # type: ignore[call-arg]

    return decorator(wrapped) if wrapped else decorator


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class EntrypointBuilder[**P, T1, T2](_EntrypointDecorator[P, T1, T2]):
    profile_loader: ProfileLoader = field(default_factory=ProfileLoader)
    __rules: list[Rule[P, Any, Any]] = field(default_factory=list, init=False)

    def __call__(
        self,
        wrapped: Callable[P, T1] | None = None,
        /,
        *,
        autocall: bool = False,
    ) -> Any:
        def decorator(wp: Callable[P, T1]) -> Callable[P, T2]:
            wrapper = self._apply(wp)

            if autocall:
                wrapper()  # type: ignore[call-arg]

            return wrapper

        return decorator(wrapped) if wrapped else decorator

    def async_to_sync[_T](
        self: EntrypointBuilder[P, T1, Awaitable[_T]],
        run: Callable[[Coroutine[Any, Any, _T]], _T] = asyncio.run,
        /,
    ) -> EntrypointBuilder[P, T1, _T]:
        return self._add_rule(_AsyncToSyncRule(run))  # type: ignore[arg-type]

    def decorate[_T](
        self,
        decorator: Callable[[Callable[P, T2]], Callable[P, _T]],
        /,
    ) -> EntrypointBuilder[P, T1, _T]:
        return self._add_rule(_DecorateRule(decorator))

    def inject(self) -> Self:
        self._add_rule(_InjectRule(self.profile_loader.module))
        return self

    def load_modules(
        self,
        loader: PythonModuleLoader,
        *packages: PythonModule | str,
    ) -> Self:
        self._add_rule(_LoadModulesRule(loader, packages))
        return self

    def load_profile(self, name: str, /) -> Self:
        self._add_rule(_LoadProfileRule(self.profile_loader, name))
        return self

    def _add_rule[_T](
        self,
        rule: Rule[P, T2, _T],
    ) -> EntrypointBuilder[P, T1, _T]:
        self.__rules.append(rule)
        return self  # type: ignore[return-value]

    def _apply(self, function: Callable[P, T1], /) -> Callable[P, T2]:
        for rule in self.__rules:
            function = rule.apply(function)

        return function  # type: ignore[return-value]
