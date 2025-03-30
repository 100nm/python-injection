from abc import abstractmethod
from collections.abc import Awaitable, Callable, Generator
from dataclasses import dataclass
from typing import Any, AsyncContextManager, NoReturn, Protocol, runtime_checkable


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SimpleAwaitable[T](Awaitable[T]):
    callable: Callable[..., Awaitable[T]]

    def __await__(self) -> Generator[Any, Any, T]:
        return self.callable().__await__()


@runtime_checkable
class Caller[**P, T](Protocol):
    __slots__ = ()

    @abstractmethod
    async def acall(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError

    @abstractmethod
    def call(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class AsyncCaller[**P, T](Caller[P, T]):
    callable: Callable[P, Awaitable[T]]

    async def acall(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return await self.callable(*args, **kwargs)

    def call(self, /, *args: P.args, **kwargs: P.kwargs) -> NoReturn:
        raise RuntimeError("Can't call async callable synchronously.")


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class SyncCaller[**P, T](Caller[P, T]):
    callable: Callable[P, T]

    async def acall(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.callable(*args, **kwargs)

    def call(self, /, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.callable(*args, **kwargs)


try:
    import anyio

    def create_semaphore(value: int) -> AsyncContextManager[Any]:
        return anyio.Semaphore(value)
except ImportError:  # pragma: no cover
    import asyncio

    def create_semaphore(value: int) -> AsyncContextManager[Any]:
        return asyncio.Semaphore(value)
