from injection.common.tools import format_type

__all__ = (
    "InjectionError",
    "NoInjectable",
    "ModuleError",
    "ModuleLockError",
    "ModuleNotUsedError",
)


class InjectionError(Exception):
    __slots__ = ()


class NoInjectable(KeyError, InjectionError):
    __slots__ = ("__class",)

    def __init__(self, cls: type):
        super().__init__(f"No injectable for `{format_type(cls)}`.")
        self.__class = cls

    @property
    def cls(self) -> type:
        return self.__class


class ModuleError(InjectionError):
    __slots__ = ()


class ModuleLockError(ModuleError):
    __slots__ = ()


class ModuleNotUsedError(KeyError, ModuleError):
    __slots__ = ()
