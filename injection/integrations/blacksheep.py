from typing import Any, TypeVar

from injection import Module, default_module

__all__ = ("InjectionServices",)

_T = TypeVar("_T")


class InjectionServices:
    """
    BlackSheep dependency injection container implemented with `python-injection`.
    """

    __slots__ = ("__module",)

    def __init__(self, module: Module = default_module):
        self.__module = module

    def __contains__(self, cls: type | Any, /) -> bool:
        return cls in self.__module

    def register(self, cls: type | Any, *__args, **__kwargs):
        self.__module.injectable(cls)
        return self

    def resolve(self, cls: type[_T] | Any, *__args, **__kwargs) -> _T:
        return self.__module.get_instance(cls, none=False)
