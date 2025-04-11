import pytest

from injection.utils import PythonModuleLoader, load_packages


class TestPythonModuleLoader:
    def test_load_with_predicate(self):
        from tests.utils import package1

        loaded_modules = (
            PythonModuleLoader(lambda name: ".excluded_package." not in name)
            .load(package1)
            .modules
        )

        assert "tests.utils.package1.excluded_package.module3" not in loaded_modules

        modules = (
            "tests.utils.package1.module1",
            "tests.utils.package1.sub_package.module2",
        )

        for module in modules:
            assert module in loaded_modules

    def test_load_with_keywords(self):
        from tests.utils import package2

        loaded_modules = (
            PythonModuleLoader.from_keywords("@injectable").load(package2).modules
        )

        assert len(loaded_modules) == 1
        assert "tests.utils.package2.sub_package.injectable" in loaded_modules

    def test_load_with_startswith(self):
        from tests.utils import package1

        loaded_modules = PythonModuleLoader.startswith("prefix_").load(package1).modules

        assert len(loaded_modules) == 1
        assert "tests.utils.package1.prefix_module" in loaded_modules

    def test_load_with_endswith(self):
        from tests.utils import package1

        loaded_modules = PythonModuleLoader.endswith("_suffix").load(package1).modules

        assert len(loaded_modules) == 1
        assert "tests.utils.package1.module_suffix" in loaded_modules

    def test_load_packages_with_success(self):
        from tests.utils import package1

        loaded_modules = load_packages(package1)

        modules = (
            "tests.utils.package1.module1",
            "tests.utils.package1.module_suffix",
            "tests.utils.package1.prefix_module",
            "tests.utils.package1.sub_package.module2",
            "tests.utils.package1.excluded_package.module3",
        )

        for module in modules:
            assert module in loaded_modules

    def test_load_packages_with_str(self):
        loaded_modules = load_packages("tests.utils.package1")

        modules = (
            "tests.utils.package1.module1",
            "tests.utils.package1.module_suffix",
            "tests.utils.package1.prefix_module",
            "tests.utils.package1.sub_package.module2",
            "tests.utils.package1.excluded_package.module3",
        )

        for module in modules:
            assert module in loaded_modules

    def test_load_packages_with_module_raise_type_error(self):
        from tests.utils.package1 import module1

        with pytest.raises(TypeError):
            load_packages(module1)
