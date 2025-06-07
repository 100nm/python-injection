from collections.abc import Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any

from injection._core.common.asynchronous import Caller
from injection._core.module import Module, mod


def asfunction[**P, T](
    wrapped: type[Callable[P, T]] | None = None,
    /,
    *,
    module: Module | None = None,
    threadsafe: bool | None = None,
) -> Any:
    module = module or mod()

    def decorator(wp: type[Callable[P, T]]) -> Callable[P, T]:
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
