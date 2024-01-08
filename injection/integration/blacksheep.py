from typing import Any, TypeVar

from injection import Module, default_module

_T = TypeVar("_T")


class InjectionDI:
    """
    BlackSheep DI container implemented with `python-injection`
    """

    __slots__ = ("__module",)

    def __init__(self, module: Module = default_module):
        self.__module = module

    def __contains__(self, cls: type | Any) -> bool:
        return cls in self.__module

    def register(self, cls: type | Any, *args, **kwargs):
        kwargs.setdefault("auto_inject", False)
        self.__module.injectable(cls, *args, **kwargs)

    def resolve(self, cls: type[_T] | Any, *args, **kwargs) -> _T | None:
        return self.__module.get_instance(cls, *args, **kwargs)
