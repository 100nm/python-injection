from collections.abc import Callable
from types import GenericAlias
from typing import Any, TypeAliasType

from injection import Module, mod
from injection.exceptions import InjectionError
from injection.integrations import _is_installed

__all__ = ("Inject",)

if _is_installed("fastapi", __name__):
    from fastapi import Depends


def Inject[T](  # noqa: N802
    cls: type[T] | TypeAliasType | GenericAlias,
    /,
    module: Module | None = None,
    *,
    scoped: bool = True,
) -> Any:
    """
    Declare a FastAPI dependency with `python-injection`.
    """

    dependency: InjectionDependency[T] = InjectionDependency(cls, module or mod())
    return Depends(dependency, use_cache=scoped)


class InjectionDependency[T]:
    __slots__ = ("__call__", "__class")

    __call__: Callable[[], T]
    __class: type[T] | TypeAliasType | GenericAlias

    def __init__(self, cls: type[T] | TypeAliasType | GenericAlias, module: Module):
        lazy_instance = module.get_lazy_instance(cls)
        self.__call__ = lambda: self.__ensure(~lazy_instance)
        self.__class = cls

    def __eq__(self, other: Any) -> bool:
        cls = type(self)
        return isinstance(other, cls) and hash(self) == hash(other)

    def __hash__(self) -> int:
        return hash((self.__class,))

    def __ensure(self, instance: T | None) -> T:
        if instance is None:
            raise InjectionError(f"`{self.__class}` is an unknown dependency.")

        return instance
