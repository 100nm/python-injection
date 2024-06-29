import pytest
from faker import Faker

from injection import Module as InjectionModule
from injection import default_module
from injection.utils import load_package

testing = InjectionModule(f"{__name__}:testing")


@pytest.fixture(scope="session", autouse=True)
def setup_test_dependencies():
    from .tests import injectables

    load_package(injectables)
    default_module.init_modules(testing)


@pytest.fixture(scope="function", autouse=True)
def clear_cache_dependencies():
    yield
    default_module.unlock()


@pytest.fixture(scope="function", autouse=True)
def setup_faker():
    Faker.seed(0)
