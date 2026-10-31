from types import ModuleType as PythonModule

import pytest

from injection._core.module import Module, mod
from injection.loaders import (
    ProfileLoader,
    PythonModuleLoader,
    load_packages,
    load_profile,
)
from tests.packages import package1, package2
from tests.packages.package1 import module1


class A: ...


class B(A): ...


@pytest.mark.parametrize("package", [package1, "tests.packages.package1"])
def test_load_packages_with_package_returns_modules(
    package: PythonModule | str,
) -> None:
    modules = load_packages(package)

    assert modules.keys() == {
        "tests.packages.package1.excluded_package.module3",
        "tests.packages.package1.module1",
        "tests.packages.package1.module_suffix",
        "tests.packages.package1.prefix_module",
        "tests.packages.package1.sub_package.module2",
    }


def test_load_packages_with_predicate_returns_matching_modules() -> None:
    modules = load_packages(
        package1,
        predicate=lambda name: ".excluded_package." not in name,
    )

    assert "tests.packages.package1.excluded_package.module3" not in modules
    assert "tests.packages.package1.module1" in modules


def test_load_packages_with_module_raises_type_error() -> None:
    with pytest.raises(TypeError):
        load_packages(module1)


def test_load_profile_with_profile_name_returns_loaded_profile() -> None:
    root = Module("root")
    root.injectable(A)
    mod("load_profile").injectable(on=A)(B)

    with load_profile("load_profile", ProfileLoader(module=root)):
        assert type(root.find_instance(A)) is B

    assert type(root.find_instance(A)) is A


class TestPythonModuleLoader:
    def test_load_with_loaded_module_returns_loader(self) -> None:
        loader = PythonModuleLoader(lambda name: name.endswith("module1"))
        loader.load(package1)

        modules = loader.load(package1).modules

        assert modules.keys() == {"tests.packages.package1.module1"}

    def test_fnmatch_with_pattern_returns_loader(self) -> None:
        loader = PythonModuleLoader.fnmatch("*.sub_package.*")

        modules = loader.load(package1).modules

        assert modules.keys() == {"tests.packages.package1.sub_package.module2"}

    def test_from_keywords_with_keyword_returns_loader(self) -> None:
        loader = PythonModuleLoader.from_keywords("@injectable")

        modules = loader.load(package2).modules

        assert modules.keys() == {"tests.packages.package2.sub_package.injectable"}

    @pytest.mark.parametrize("module_name", ["unknown_module", "sys"])
    def test_from_keywords_without_python_file_returns_loader_ignoring_module(
        self,
        module_name: str,
    ) -> None:
        loader = PythonModuleLoader.from_keywords("@injectable")

        assert loader.predicate(module_name) is False

    def test_startswith_with_prefix_returns_loader(self) -> None:
        loader = PythonModuleLoader.startswith("prefix_")

        modules = loader.load(package1).modules

        assert modules.keys() == {"tests.packages.package1.prefix_module"}

    def test_endswith_with_suffix_returns_loader(self) -> None:
        loader = PythonModuleLoader.endswith("_suffix")

        modules = loader.load(package1).modules

        assert modules.keys() == {"tests.packages.package1.module_suffix"}


class TestProfileLoader:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            (None, {"root", "a", "b", "c"}),
            ("dev", {"root", "a", "b", "c", "dev", "d"}),
        ],
    )
    def test_required_module_names_with_optional_name_returns_module_names(
        self,
        expected: set[str],
        name: str | None,
    ) -> None:
        loader = ProfileLoader(
            {"root": ["a", "b"], "b": ["c"], "dev": ["d"], "test": ["t"]},
            module=Module("root"),
        )

        assert loader.required_module_names(name) == expected

    def test_init_with_module_subsets_returns_loader(self) -> None:
        root = Module("root")
        mod("profile_loader_init").injectable(A)
        loader = ProfileLoader({"root": ["profile_loader_init"]}, module=root)

        loader.init()

        assert A in root

    def test_load_with_profile_subsets_returns_loaded_profile(self) -> None:
        root = Module("root")
        root.injectable(A)
        mod("profile_loader_load_subset").injectable(on=A)(B)
        loader = ProfileLoader(
            {"profile_loader_load": ["profile_loader_load_subset"]},
            module=root,
        )

        with loader.load("profile_loader_load"):
            assert type(root.find_instance(A)) is B

        assert type(root.find_instance(A)) is A

    def test_load_with_default_profile_returns_loaded_profile(self) -> None:
        root = Module("root")
        loader = ProfileLoader({"root": ["profile_loader_default"]}, module=root)
        mod("profile_loader_default").injectable(A)

        with loader.load("root"):
            assert A in root


class TestLoadedProfile:
    def test_reload_with_unloaded_profile_returns_loaded_profile(self) -> None:
        root = Module("root")
        mod("loaded_profile_reload").injectable(A)
        profile = load_profile("loaded_profile_reload", ProfileLoader(module=root))
        profile.unload()

        with profile.reload():
            assert A in root

        assert A not in root
