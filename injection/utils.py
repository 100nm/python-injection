from collections.abc import Callable, Iterator
from contextlib import contextmanager
from importlib import import_module
from pkgutil import walk_packages
from types import ModuleType as PythonModule
from typing import ContextManager

from injection import mod

__all__ = ("load_packages", "load_profile")


def load_profile(name: str, /, *other_profile_names: str) -> ContextManager[None]:
    """
    Injection module initialization function based on profile name.
    A profile name is equivalent to an injection module name.
    """

    modules = tuple(mod(module_name) for module_name in (name, *other_profile_names))

    for module in modules:
        module.unlock()

    target = mod().unlock().init_modules(*modules)

    del module, modules

    @contextmanager
    def cleaner() -> Iterator[None]:
        yield
        target.unlock().init_modules()

    return cleaner()


def load_packages(
    *packages: PythonModule | str,
    predicate: Callable[[str], bool] = lambda module_name: True,
) -> dict[str, PythonModule]:
    """
    Function for importing all modules in a Python package.
    Pass the `predicate` parameter if you want to filter the modules to be imported.
    """

    loaded: dict[str, PythonModule] = {}

    for package in packages:
        if isinstance(package, str):
            package = import_module(package)

        loaded |= __iter_modules_from(package, predicate)

    return loaded


def __iter_modules_from(
    package: PythonModule,
    predicate: Callable[[str], bool],
) -> Iterator[tuple[str, PythonModule]]:
    package_name = package.__name__

    try:
        package_path = package.__path__
    except AttributeError as exc:
        raise TypeError(f"`{package_name}` isn't Python package.") from exc

    for info in walk_packages(path=package_path, prefix=f"{package_name}."):
        name = info.name

        if info.ispkg or not predicate(name):
            continue

        yield name, import_module(name)
