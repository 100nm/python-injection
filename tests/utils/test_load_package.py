import sys

import pytest

from injection.utils import load_package


class TestLoadPackage:
    def test_load_package_with_predicate(self):
        from tests.utils import package

        load_package(package, predicate=lambda name: ".excluded_package." not in name)

        assert "tests.utils.package.excluded_package.module3" not in sys.modules

        modules = (
            "tests.utils.package.module1",
            "tests.utils.package.sub_package.module2",
        )

        for module in modules:
            assert module in sys.modules

    def test_load_package_with_success(self):
        from tests.utils import package

        load_package(package)

        modules = (
            "tests.utils.package.module1",
            "tests.utils.package.sub_package.module2",
            "tests.utils.package.excluded_package.module3",
        )

        for module in modules:
            assert module in sys.modules

    def test_load_package_with_str(self):
        load_package("tests.utils.package")

        modules = (
            "tests.utils.package.module1",
            "tests.utils.package.sub_package.module2",
            "tests.utils.package.excluded_package.module3",
        )

        for module in modules:
            assert module in sys.modules

    def test_load_package_with_module_raise_type_error(self):
        from tests.utils.package import module1

        with pytest.raises(TypeError):
            load_package(module1)
