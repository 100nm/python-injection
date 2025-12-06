from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from functools import wraps
from types import ModuleType as PythonModule
from typing import TYPE_CHECKING, Any, Concatenate, Protocol, Self, final, overload

from injection import Module
from injection.loaders import ProfileLoader, PythonModuleLoader

__all__ = ("AsyncEntrypoint", "Entrypoint", "entrypointmaker")


type AsyncEntrypoint[**P, T] = Entrypoint[P, Coroutine[Any, Any, T]]
type EntrypointSetupMethod[**P, **EPP, T1, T2] = Callable[
    Concatenate[Entrypoint[EPP, T1], P],
    Entrypoint[EPP, T2],
]


class _EntrypointDecorator[**P, T1, T2](Protocol):
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

    def __call__(
        self,
        wrapped: Callable[P, T1] | None = ...,
        /,
        *,
        autocall: bool = ...,
    ) -> Any: ...


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
        return Entrypoint._make_decorator(wp, profile_loader)

    return decorator(wrapped) if wrapped else decorator


@final
@dataclass(repr=False, eq=False, frozen=True, slots=True)
class Entrypoint[**P, T]:
    function: Callable[P, T]
    profile_loader: ProfileLoader = field(default_factory=ProfileLoader)

    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.function(*args, **kwargs)

    @property
    def __module(self) -> Module:
        return self.profile_loader.module

    def async_to_sync[_T](
        self: AsyncEntrypoint[P, _T],
        run: Callable[[Coroutine[Any, Any, _T]], _T] = asyncio.run,
        /,
    ) -> Entrypoint[P, _T]:
        function = self.function

        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> _T:
            return run(function(*args, **kwargs))

        return self.__recreate(wrapper)

    def decorate(
        self,
        decorator: Callable[[Callable[P, T]], Callable[P, T]],
        /,
    ) -> Self:
        return self.__recreate(decorator(self.function))

    def inject(self) -> Self:
        return self.decorate(self.__module.make_injected_function)

    def load_modules(
        self,
        /,
        loader: PythonModuleLoader,
        *packages: PythonModule | str,
    ) -> Self:
        return self.setup(lambda: loader.load(*packages))

    def load_profile(self, name: str, /) -> Self:
        @contextmanager
        def decorator(loader: ProfileLoader) -> Iterator[None]:
            with loader.load(name):
                yield

        return self.decorate(decorator(self.profile_loader))

    def setup(self, function: Callable[..., Any], /) -> Self:
        @contextmanager
        def decorator() -> Iterator[Any]:
            yield function()

        return self.decorate(decorator())

    def async_setup[_T](
        self: AsyncEntrypoint[P, _T],
        function: Callable[..., Awaitable[Any]],
        /,
    ) -> AsyncEntrypoint[P, _T]:
        @asynccontextmanager
        async def decorator() -> AsyncIterator[Any]:
            yield await function()

        return self.decorate(decorator())

    def __recreate[**_P, _T](
        self: Entrypoint[Any, Any],
        function: Callable[_P, _T],
        /,
    ) -> Entrypoint[_P, _T]:
        return type(self)(function, self.profile_loader)

    @classmethod
    def _make_decorator[**_P, _T](
        cls,
        setup_method: EntrypointSetupMethod[_P, P, T, _T],
        /,
        profile_loader: ProfileLoader | None = None,
    ) -> _EntrypointDecorator[P, T, _T]:
        profile_loader = profile_loader or ProfileLoader()
        setup_method = profile_loader.module.make_injected_function(setup_method)

        def entrypoint_decorator(
            wrapped: Callable[P, T] | None = None,
            /,
            *,
            autocall: bool = False,
        ) -> Any:
            def decorator(wp: Callable[P, T]) -> Callable[P, _T]:
                profile_loader.init()
                self = cls(wp, profile_loader)
                wrapper = setup_method(self).function  # type: ignore[call-arg]

                if autocall:
                    wrapper()  # type: ignore[call-arg]

                return wrapper

            return decorator(wrapped) if wrapped else decorator

        return entrypoint_decorator
