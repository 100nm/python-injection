from importlib import import_module
from pkgutil import walk_packages
from types import ModuleType as Package


def load_package(package: Package):
    try:
        path = package.__path__
    except AttributeError as exc:
        raise TypeError(
            "Package has no `__path__` attribute, as it's probably a module."
        ) from exc

    for info in walk_packages(path, prefix=f"{package.__name__}."):
        if info.ispkg:
            continue

        import_module(info.name)


__all__ = ("load_package",)
