from collections.abc import Callable
from typing import Any

from injection import Module, mod
from injection.integrations import _is_installed

__all__ = ("Inject",)

if _is_installed("fastapi", __name__):
    from fastapi import Depends


def Inject[T](cls: type[T] | Any, /, module: Module | None = None) -> Any:  # noqa: N802
    """
    Declare a FastAPI dependency with `python-injection`.
    """

    dependency: InjectionDependency[T] = InjectionDependency(cls, module or mod())
    return Depends(dependency)


class InjectionDependency[T]:
    __slots__ = ("__call__",)

    __call__: Callable[[], T | None]

    def __init__(self, cls: type[T] | Any, module: Module):
        lazy_instance = module.get_lazy_instance(cls)
        self.__call__ = lambda: ~lazy_instance
