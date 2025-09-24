from abc import abstractmethod
from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Protocol, runtime_checkable

from injection._core.common.asynchronous import Caller
from injection._core.module import Module, mod

type AsFunctionWrappedType[**P, T] = type[AsFunctionCallable[P, T]]


@runtime_checkable
class AsFunctionCallable[**P, T](Protocol):
    __slots__ = ()

    @abstractmethod
    def call(self, *args: P.args, **kwargs: P.kwargs) -> T:
        raise NotImplementedError


def asfunction[**P, T](
    wrapped: AsFunctionWrappedType[P, T] | None = None,
    /,
    *,
    module: Module | None = None,
    threadsafe: bool | None = None,
) -> Any:
    module = module or mod()

    def decorator(wp: AsFunctionWrappedType[P, T]) -> Callable[P, T]:
        fake_method = wp.call.__get__(NotImplemented)
        factory: Caller[..., AsFunctionCallable[P, T]] = module.make_injected_function(
            wp,
            threadsafe=threadsafe,
        ).__inject_metadata__

        wrapper: Callable[P, T]

        if iscoroutinefunction(fake_method):

            @wraps(fake_method)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                self = await factory.acall()
                return await self.call(*args, **kwargs)  # type: ignore[misc]

        else:

            @wraps(fake_method)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                self = factory.call()
                return self.call(*args, **kwargs)

        wrapper.__name__ = wp.__name__
        wrapper.__qualname__ = wp.__qualname__
        return wrapper

    return decorator(wrapped) if wrapped else decorator
