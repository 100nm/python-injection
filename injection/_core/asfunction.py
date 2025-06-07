from abc import abstractmethod
from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Protocol, runtime_checkable

from injection._core.common.asynchronous import Caller
from injection._core.module import Module, mod

type AsFunctionWrappedType[**P, T] = type[_Callable[P, T]]


@runtime_checkable
class _Callable[**P, T](Protocol):
    __slots__ = ()

    @abstractmethod
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
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
        get_method = wp.__call__.__get__
        method = get_method(NotImplemented)
        factory: Caller[..., Callable[P, T]] = module.make_injected_function(
            wp,
            threadsafe=threadsafe,
        ).__inject_metadata__

        wrapper: Callable[P, T]

        if iscoroutinefunction(method):

            @wraps(method)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                self = await factory.acall()
                return await get_method(self)(*args, **kwargs)

        else:

            @wraps(method)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                self = factory.call()
                return get_method(self)(*args, **kwargs)

        wrapper.__name__ = wp.__name__
        wrapper.__qualname__ = wp.__qualname__
        return wrapper

    return decorator(wrapped) if wrapped else decorator
