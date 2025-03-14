from typing import Any

__all__ = (
    "EmptySlotError",
    "InjectionError",
    "ModuleError",
    "ModuleLockError",
    "ModuleNotUsedError",
    "NoInjectable",
    "ScopeAlreadyDefinedError",
    "ScopeError",
    "ScopeUndefinedError",
    "SkipInjectable",
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


class SkipInjectable(InjectionError): ...


class EmptySlotError(SkipInjectable, InjectionError): ...


class ModuleError(InjectionError): ...


class ModuleLockError(ModuleError): ...


class ModuleNotUsedError(KeyError, ModuleError): ...


class ScopeError(InjectionError): ...


class ScopeUndefinedError(LookupError, SkipInjectable, ScopeError): ...


class ScopeAlreadyDefinedError(ScopeError): ...
