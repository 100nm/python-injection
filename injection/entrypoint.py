from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from functools import wraps
from types import MethodType
from types import ModuleType as PythonModule
from typing import Any, Self, final, overload

from injection import Module, mod
from injection.loaders import PythonModuleLoader

__all__ = ("AsyncEntrypoint", "Entrypoint", "autocall", "entrypointmaker")

type AsyncEntrypoint[**P, T] = Entrypoint[P, Coroutine[Any, Any, T]]
type EntrypointDecorator[**P, T1, T2] = Callable[[Callable[P, T1]], Callable[P, T2]]
type EntrypointSetupMethod[*Ts, **P, T1, T2] = Callable[
    [Entrypoint[P, T1], *Ts],
    Entrypoint[P, T2],
]


def autocall[**P, T](wrapped: Callable[P, T] | None = None, /) -> Any:
    def decorator(wp: Callable[P, T]) -> Callable[P, T]:
        wp()  # type: ignore[call-arg]
        return wp

    return decorator(wrapped) if wrapped else decorator


@overload
def entrypointmaker[*Ts, **P, T1, T2](
    wrapped: EntrypointSetupMethod[*Ts, P, T1, T2],
    /,
    *,
    module: Module = ...,
) -> EntrypointDecorator[P, T1, T2]: ...


@overload
def entrypointmaker[*Ts, **P, T1, T2](
    wrapped: None = ...,
    /,
    *,
    module: Module = ...,
) -> Callable[
    [EntrypointSetupMethod[*Ts, P, T1, T2]],
    EntrypointDecorator[P, T1, T2],
]: ...


def entrypointmaker[*Ts, **P, T1, T2](
    wrapped: EntrypointSetupMethod[*Ts, P, T1, T2] | None = None,
    /,
    *,
    module: Module | None = None,
) -> Any:
    def decorator(
        wp: EntrypointSetupMethod[*Ts, P, T1, T2],
    ) -> EntrypointDecorator[P, T1, T2]:
        return Entrypoint._make_decorator(wp, module)

    return decorator(wrapped) if wrapped else decorator


@final
@dataclass(repr=False, eq=False, frozen=True, slots=True)
class Entrypoint[**P, T]:
    function: Callable[P, T]
    module: Module = field(default_factory=mod)

    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.function(*args, **kwargs)

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
        return self.decorate(self.module.make_injected_function)

    def load_modules(
        self,
        /,
        loader: PythonModuleLoader,
        *packages: PythonModule | str,
    ) -> Self:
        return self.setup(lambda: loader.load(*packages))

    def load_profile(self, /, *names: str) -> Self:
        @contextmanager
        def decorator(module: Module) -> Iterator[None]:
            with module.load_profile(*names):
                yield

        return self.decorate(decorator(self.module))

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
        return type(self)(function, self.module)

    @classmethod
    def _make_decorator[*Ts, _T](
        cls,
        setup_method: EntrypointSetupMethod[*Ts, P, T, _T],
        /,
        module: Module | None = None,
    ) -> EntrypointDecorator[P, T, _T]:
        module = module or mod()
        setup_method = module.make_injected_function(setup_method)

        def decorator(function: Callable[P, T]) -> Callable[P, _T]:
            self = cls(function, module)
            return MethodType(setup_method, self)().function

        return decorator
