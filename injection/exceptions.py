class InjectionError(Exception):
    ...


class NoInjectable(KeyError, InjectionError):
    ...


class ModuleError(InjectionError):
    ...


class ModuleCircularUseError(ModuleError):
    ...


class ModuleNotUsedError(KeyError, ModuleError):
    ...
