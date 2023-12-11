from injection.common.formatting import format_type

__all__ = (
    "InjectionError",
    "NoInjectable",
    "ModuleError",
    "ModuleCircularUseError",
    "ModuleNotUsedError",
)


class InjectionError(Exception):
    __slots__ = ()


class NoInjectable(KeyError, InjectionError):
    __slots__ = ("__reference",)

    def __init__(self, reference: type):
        super().__init__(f"No injectable for `{format_type(reference)}`.")
        self.__reference = reference

    @property
    def reference(self) -> type:
        return self.__reference


class ModuleError(InjectionError):
    __slots__ = ()


class ModuleCircularUseError(ModuleError):
    __slots__ = ()


class ModuleNotUsedError(KeyError, ModuleError):
    __slots__ = ()
