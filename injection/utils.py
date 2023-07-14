from importlib import import_module
from pkgutil import walk_packages
from types import ModuleType as Package


def load_package(package: Package):
    if not hasattr(package, "__path__"):
        raise TypeError(
            "Package has no `__path__` attribute, as it's probably a module."
        )

    for info in walk_packages(package.__path__, prefix=f"{package.__name__}."):
        if info.ispkg:
            continue

        import_module(info.name)
