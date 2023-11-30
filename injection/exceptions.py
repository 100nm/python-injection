__all__ = ("InjectionError", "ModuleError", "NoInjectable")


class InjectionError(Exception):
    ...


class NoInjectable(KeyError, InjectionError):
    ...


class ModuleError(InjectionError):
    ...
