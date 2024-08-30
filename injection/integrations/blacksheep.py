from typing import Any, override

from injection import Module, mod
from injection.integrations import _is_installed

__all__ = ("InjectionServices",)

if _is_installed("blacksheep", __name__):
    from rodi import ContainerProtocol


class InjectionServices(ContainerProtocol):
    """
    BlackSheep dependency injection container implemented with `python-injection`.
    """

    __slots__ = ("__module",)

    __module: Module

    def __init__(self, module: Module | None = None) -> None:
        self.__module = module or mod()

    @override
    def __contains__(self, item: Any) -> bool:
        return item in self.__module

    @override
    def register(self, obj_type: type | Any, *args: Any, **kwargs: Any) -> None:
        self.__module.injectable(obj_type)

    @override
    def resolve[T](self, obj_type: type[T] | Any, *args: Any, **kwargs: Any) -> T:
        return self.__module.find_instance(obj_type)
