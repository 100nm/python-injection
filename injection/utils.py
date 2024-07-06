from collections.abc import Callable
from importlib import import_module
from pkgutil import walk_packages
from types import ModuleType

__all__ = ("load_package",)


def load_package(package: ModuleType | str, predicate: Callable[[str], bool] = None):
    """
    Function for importing all modules in a Python package.
    Pass the `predicate` parameter if you want to filter the modules to be imported.
    """

    if isinstance(package, str):
        package = import_module(package)

    try:
        path = package.__path__
    except AttributeError as exc:
        raise TypeError(
            "Package has no `__path__` attribute, as it's probably a module."
        ) from exc

    if predicate is None:

        def predicate(_: str) -> bool:
            return True

    for info in walk_packages(path=path, prefix=f"{package.__name__}."):
        name = info.name

        if info.ispkg or not predicate(name):
            continue

        import_module(name)
