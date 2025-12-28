from collections.abc import Awaitable, Callable
from functools import update_wrapper
from inspect import iscoroutinefunction
from typing import Any, Protocol

from injection._core.common.asynchronous import Caller
from injection._core.module import InjectMetadata, Module, mod


class _AsFunctionCallable[**P, T](Protocol):
    def __call__(self, /, *args: P.args, **kwargs: P.kwargs) -> T: ...


type AsFunctionWrappedType[**P, T] = type[_AsFunctionCallable[P, T]]


def asfunction[**P, T](
    wrapped: AsFunctionWrappedType[P, T] | None = None,
    /,
    *,
    module: Module | None = None,
    threadsafe: bool | None = None,
) -> Any:
    def decorator(wp: AsFunctionWrappedType[P, T]) -> Callable[P, T]:
        fake_method = wp.__call__.__get__(NotImplemented, wp)
        metadata: InjectMetadata[..., Callable[P, T]] = (
            module or mod()
        ).create_metadata(wp, threadsafe)

        wrapper: Callable[P, T] = (
            _wrap_async(metadata)  # type: ignore[arg-type, assignment]
            if iscoroutinefunction(fake_method)
            else _wrap_sync(metadata)
        )
        wrapper = update_wrapper(wrapper, fake_method)

        for attribute in ("__name__", "__qualname__"):
            setattr(wrapper, attribute, getattr(wp, attribute))

        return wrapper

    return decorator(wrapped) if wrapped else decorator


def _wrap_async[**P, T](
    factory: Caller[..., Callable[P, Awaitable[T]]],
) -> Callable[P, Awaitable[T]]:
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        self = await factory.acall()
        return await self(*args, **kwargs)

    return wrapper


def _wrap_sync[**P, T](factory: Caller[..., Callable[P, T]]) -> Callable[P, T]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        self = factory.call()
        return self(*args, **kwargs)

    return wrapper
