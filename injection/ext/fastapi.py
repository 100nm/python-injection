from types import GenericAlias
from typing import Any, TypeAliasType

from fastapi import Depends

from injection import Module, mod

__all__ = ("Inject",)


def Inject[T](  # noqa: N802
    cls: type[T] | TypeAliasType | GenericAlias,
    /,
    default: T = NotImplemented,
    module: Module | None = None,
) -> Any:
    """
    Declare a FastAPI dependency with `python-injection`.
    """

    module = module or mod()
    lazy_instance = module.aget_lazy_instance(cls, default)

    async def getter() -> T:
        return await lazy_instance

    return Depends(getter, use_cache=False)
