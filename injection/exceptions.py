from typing import Any

__all__ = (
    "HookError",
    "InjectionError",
    "ModuleError",
    "ModuleLockError",
    "ModuleNotUsedError",
    "NoInjectable",
)


class InjectionError(Exception): ...


class NoInjectable[T](KeyError, InjectionError):
    __slots__ = ("__class",)

    __class: type[T]

    def __init__(self, cls: type[T] | Any) -> None:
        super().__init__(f"No injectable for `{cls}`.")
        self.__class = cls

    @property
    def cls(self) -> type[T]:
        return self.__class


class ModuleError(InjectionError): ...


class ModuleLockError(ModuleError): ...


class ModuleNotUsedError(KeyError, ModuleError): ...


class HookError(InjectionError): ...
