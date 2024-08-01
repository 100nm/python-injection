import pytest
from faker import Faker

from injection.testing import use_test_injectables
from injection.utils import load_packages


@pytest.fixture(scope="session", autouse=True)
def autouse_test_injectables():
    from .tests import injectables

    load_packages(injectables)

    with use_test_injectables():
        yield


@pytest.fixture(scope="function", autouse=True)
def setup_faker():
    Faker.seed(0)
