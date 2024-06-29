from typing import Any

__all__ = (
    "InjectionError",
    "NoInjectable",
    "ModuleError",
    "ModuleLockError",
    "ModuleNotUsedError",
)


class InjectionError(Exception):
    pass


class NoInjectable[T](KeyError, InjectionError):
    __slots__ = ("__class",)

    def __init__(self, cls: type[T] | Any):
        super().__init__(f"No injectable for `{cls}`.")
        self.__class = cls

    @property
    def cls(self) -> type[T]:
        return self.__class


class ModuleError(InjectionError):
    pass


class ModuleLockError(ModuleError):
    pass


class ModuleNotUsedError(KeyError, ModuleError):
    pass
