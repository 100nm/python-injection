from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Coroutine, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from functools import wraps
from types import MethodType
from types import ModuleType as PythonModule
from typing import Any, Self, final

from injection import Module, mod
from injection.loaders import PythonModuleLoader

__all__ = ("AsyncRunner", "Runner")

type AsyncRunner[**P, T] = Runner[P, Coroutine[Any, Any, T]]


@final
@dataclass(repr=False, eq=False, frozen=True, slots=True)
class Runner[**P, T]:
    function: Callable[P, T]
    module: Module = field(default_factory=mod)

    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.function(*args, **kwargs)

    def async_to_sync[_T](
        self: AsyncRunner[P, _T],
        run: Callable[[Coroutine[Any, Any, _T]], _T] = asyncio.run,
        /,
    ) -> Runner[P, _T]:
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

    def decorate_from_callable(
        self,
        decorator_factory: Callable[..., Callable[[Callable[P, T]], Callable[P, T]]],
        /,
        *,
        inject: bool = True,
    ) -> Self:
        function = self.function

        if not inject:
            return self.decorate(decorator_factory())

        decorator_factory = self.module.make_injected_function(decorator_factory)

        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return decorator_factory()(function)(*args, **kwargs)

        return self.__recreate(wrapper)

    def inject(self) -> Self:
        return self.decorate(self.module.make_injected_function)

    def load_modules(
        self,
        /,
        loader: PythonModuleLoader,
        *packages: PythonModule | str,
    ) -> Self:
        return self.setup(lambda: loader.load(*packages), inject=False)

    def setup[**_P](
        self,
        function: Callable[_P, Any],
        /,
        *,
        inject: bool = True,
    ) -> Self:
        @contextmanager
        @wraps(function)
        def decorator(*args: _P.args, **kwargs: _P.kwargs) -> Iterator[None]:
            function(*args, **kwargs)
            yield

        return self.decorate_from_callable(decorator, inject=inject)

    def async_setup[**_P, _T](
        self: AsyncRunner[P, _T],
        function: Callable[_P, Awaitable[Any]],
        /,
        *,
        inject: bool = True,
    ) -> AsyncRunner[P, _T]:
        @asynccontextmanager
        @wraps(function)
        async def decorator(*args: _P.args, **kwargs: _P.kwargs) -> AsyncIterator[None]:
            await function(*args, **kwargs)
            yield

        return self.decorate_from_callable(decorator, inject=inject)

    def __recreate[**_P, _T](
        self: Runner[Any, Any],
        function: Callable[_P, _T],
        /,
    ) -> Runner[_P, _T]:
        return type(self)(function, self.module)

    @classmethod
    def builder[_T, *Args](
        cls,
        setup: Callable[[Self, *Args], Runner[P, _T]],
        /,
        module: Module | None = None,
    ) -> Callable[[Callable[P, T]], Callable[P, _T]]:
        module = module or mod()
        setup = module.make_injected_function(setup)

        def decorator(function: Callable[P, T]) -> Callable[P, _T]:
            self = cls(function, module)
            return MethodType(setup, self)().function

        return decorator
