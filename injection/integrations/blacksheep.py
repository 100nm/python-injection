from typing import Any, TypeVar

from rodi import ContainerProtocol

from injection import Module, default_module

__all__ = ("InjectionServices",)

_T = TypeVar("_T")


class InjectionServices(ContainerProtocol):
    """
    BlackSheep dependency injection container implemented with `python-injection`.
    """

    __slots__ = ("__module",)

    def __init__(self, module: Module = default_module):
        self.__module = module

    def __contains__(self, item: Any) -> bool:
        return item in self.__module

    def register(self, obj_type: type | Any, *args, **kwargs):
        self.__module.injectable(obj_type)
        return self

    def resolve(self, obj_type: type[_T] | Any, *args, **kwargs) -> _T:
        return self.__module.resolve(obj_type)
