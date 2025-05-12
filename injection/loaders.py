import itertools
import sys
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from importlib import import_module
from importlib.util import find_spec
from os.path import isfile
from pkgutil import walk_packages
from types import MappingProxyType
from types import ModuleType as PythonModule
from typing import ClassVar, ContextManager, Self

from injection import Module, mod

__all__ = ("PythonModuleLoader", "load_packages", "load_profile")


def load_profile(*names: str) -> ContextManager[Module]:
    """
    Injection module initialization function based on profile name.
    A profile name is equivalent to an injection module name.
    """

    return mod().load_profile(*names)


def load_packages(
    *packages: PythonModule | str,
    predicate: Callable[[str], bool] = lambda module_name: True,
) -> dict[str, PythonModule]:
    """
    Function for importing all modules in a Python package.
    Pass the `predicate` parameter if you want to filter the modules to be imported.
    """

    return PythonModuleLoader(predicate).load(*packages).modules


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class PythonModuleLoader:
    predicate: Callable[[str], bool]
    __modules: dict[str, PythonModule | None] = field(
        default_factory=dict,
        init=False,
    )

    # To easily mock `sys.modules` in tests
    _sys_modules: ClassVar[Mapping[str, PythonModule]] = MappingProxyType(sys.modules)

    @property
    def modules(self) -> dict[str, PythonModule]:
        return {
            name: module
            for name, module in self.__modules.items()
            if module is not None
        }

    def load(self, *packages: PythonModule | str) -> Self:
        modules = itertools.chain.from_iterable(
            self.__iter_modules_from(package) for package in packages
        )
        self.__modules.update(modules)
        return self

    def __is_already_loaded(self, module_name: str) -> bool:
        return any(
            module_name in modules for modules in (self.__modules, self._sys_modules)
        )

    def __iter_modules_from(
        self,
        package: PythonModule | str,
    ) -> Iterator[tuple[str, PythonModule | None]]:
        if isinstance(package, str):
            package = import_module(package)

        package_name = package.__name__

        try:
            package_path = package.__path__
        except AttributeError as exc:
            raise TypeError(f"`{package_name}` isn't Python package.") from exc

        for info in walk_packages(path=package_path, prefix=f"{package_name}."):
            name = info.name

            if info.ispkg or self.__is_already_loaded(name):
                continue

            module = import_module(name) if self.predicate(name) else None
            yield name, module

    @classmethod
    def from_keywords(cls, *keywords: str) -> Self:
        """
        Create loader to import modules from a Python package if one of the keywords is
        contained in the Python script.
        """

        def predicate(module_name: str) -> bool:
            spec = find_spec(module_name)

            if spec is None:
                return False

            module_path = spec.origin

            if module_path is None or not isfile(module_path):
                return False

            with open(module_path, "r") as script:
                return any(keyword in line for line in script for keyword in keywords)

        return cls(predicate)

    @classmethod
    def startswith(cls, *prefixes: str) -> Self:
        def predicate(module_name: str) -> bool:
            script_name = module_name.split(".")[-1]
            return any(script_name.startswith(prefix) for prefix in prefixes)

        return cls(predicate)

    @classmethod
    def endswith(cls, *suffixes: str) -> Self:
        def predicate(module_name: str) -> bool:
            script_name = module_name.split(".")[-1]
            return any(script_name.endswith(suffix) for suffix in suffixes)

        return cls(predicate)
