import sys

import pytest

from injection.utils import load_package


class TestLoadPackage:
    def test_load_package_with_success(self):
        from tests.utils import package

        load_package(package)

        modules = (
            "tests.utils.package.module1",
            "tests.utils.package.sub_package.module2",
        )

        for module in modules:
            assert module in sys.modules

    def test_load_package_with_module_raise_type_error(self):
        from tests.utils.package import module1

        with pytest.raises(TypeError):
            load_package(module1)
