import pytest

from injection.utils import load_packages

# It isn't possible to unload a module
# So I don't know how to test it properly


@pytest.mark.skip
class TestLoadPackages:
    def test_load_packages_with_predicate(self):
        from tests.utils import package1

        loaded_modules = load_packages(
            package1,
            predicate=lambda name: ".excluded_package." not in name,
        )

        assert "tests.utils.package1.excluded_package.module3" not in loaded_modules

        modules = (
            "tests.utils.package1.module1",
            "tests.utils.package1.sub_package.module2",
        )

        for module in modules:
            assert module in loaded_modules

    def test_load_packages_with_success(self):
        from tests.utils import package1

        loaded_modules = load_packages(package1)

        modules = (
            "tests.utils.package1.module1",
            "tests.utils.package1.sub_package.module2",
            "tests.utils.package1.excluded_package.module3",
        )

        for module in modules:
            assert module in loaded_modules

    def test_load_packages_with_str(self):
        loaded_modules = load_packages("tests.utils.package1")

        modules = (
            "tests.utils.package1.module1",
            "tests.utils.package1.sub_package.module2",
            "tests.utils.package1.excluded_package.module3",
        )

        for module in modules:
            assert module in loaded_modules

    def test_load_packages_with_module_raise_type_error(self):
        from tests.utils.package1 import module1

        with pytest.raises(TypeError):
            load_packages(module1)
