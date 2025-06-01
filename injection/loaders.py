from __future__ import annotations

import itertools
import sys
from abc import abstractmethod
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from importlib import import_module
from importlib.util import find_spec
from os.path import isfile
from pkgutil import walk_packages
from types import MappingProxyType, TracebackType
from types import ModuleType as PythonModule
from typing import ClassVar, Protocol, Self, runtime_checkable

from injection import Module, Priority, mod

__all__ = (
    "LoadedProfile",
    "ProfileLoader",
    "PythonModuleLoader",
    "load_packages",
    "load_profile",
)


def load_packages(
    *packages: PythonModule | str,
    predicate: Callable[[str], bool] = lambda module_name: True,
) -> dict[str, PythonModule]:
    """
    Function for importing all modules in a Python package.
    Pass the `predicate` parameter if you want to filter the modules to be imported.
    """

    return PythonModuleLoader(predicate).load(*packages).modules


def load_profile(name: str, /, loader: ProfileLoader | None = None) -> LoadedProfile:
    """
    Injection module initialization function based on a profile name.
    A profile name is equivalent to an injection module name.
    """

    return (loader or ProfileLoader()).load(name)


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


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class ProfileLoader:
    module_subsets: Mapping[str, Sequence[str]] = field(default=MappingProxyType({}))
    module: Module = field(default_factory=mod, kw_only=True)
    __initialized_modules: set[str] = field(default_factory=set, init=False)

    @property
    def __is_empty(self) -> bool:
        return not self.module_subsets

    def required_module_names(self, name: str | None = None, /) -> frozenset[str]:
        names = {self.module.name}

        if name is not None:
            names.add(name)

        subsets = (self.__walk_subsets_for(name) for name in names)
        return frozenset(itertools.chain.from_iterable(subsets))

    def init(self) -> Self:
        self.__init_subsets_for(self.module)
        return self

    def load(self, name: str, /) -> LoadedProfile:
        self.init()

        if not self.__is_default_module(name):
            target_module = self.__init_subsets_for(mod(name))
            self.module.use(target_module, priority=Priority.HIGH)

        return _UserLoadedProfile(self, name)

    def _unload(self, name: str, /) -> None:
        self.module.unlock().stop_using(mod(name))

    def __init_subsets_for(self, module: Module) -> Module:
        if not self.__is_empty and not self.__is_initialized(module):
            target_modules = tuple(
                self.__init_subsets_for(mod(name))
                for name in self.module_subsets.get(module.name, ())
            )
            module.init_modules(*target_modules)
            self.__mark_initialized(module)

        return module

    def __is_default_module(self, module_name: str) -> bool:
        return module_name == self.module.name

    def __is_initialized(self, module: Module) -> bool:
        return module.name in self.__initialized_modules

    def __mark_initialized(self, module: Module) -> None:
        self.__initialized_modules.add(module.name)

    def __walk_subsets_for(self, module_name: str) -> Iterator[str]:
        yield module_name

        for name in self.module_subsets.get(module_name, ()):
            yield from self.__walk_subsets_for(name)


@runtime_checkable
class LoadedProfile(Protocol):
    __slots__ = ()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.unload()

    @abstractmethod
    def reload(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> Self:
        raise NotImplementedError


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class _UserLoadedProfile(LoadedProfile):
    loader: ProfileLoader
    name: str

    def reload(self) -> Self:
        self.loader.load(self.name)
        return self

    def unload(self) -> Self:
        self.loader._unload(self.name)
        return self
