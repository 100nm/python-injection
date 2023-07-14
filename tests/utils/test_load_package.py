import sys
from unittest import TestCase

import pytest

from injection.utils import load_package


class TestLoadPackage(TestCase):
    def test_load_package_with_success(self):
        from tests.utils import package

        load_package(package)
        assert "tests.utils.package.module1" in sys.modules
        assert "tests.utils.package.sub_package.module2" in sys.modules

    def test_load_package_with_module_raise_type_error(self):
        from tests.utils.package import module1

        with pytest.raises(TypeError):
            load_package(module1)
