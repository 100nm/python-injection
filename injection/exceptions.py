__all__ = ("InjectionError", "NoInjectable")


class InjectionError(Exception):
    ...


class NoInjectable(InjectionError):
    ...
