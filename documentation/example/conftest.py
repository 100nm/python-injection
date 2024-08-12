import pytest
from faker import Faker

from injection.testing import load_test_profile
from injection.utils import load_packages


@pytest.fixture(scope="session", autouse=True)
def autouse_test_injectables():
    from .tests import injectables

    load_packages(injectables)

    with load_test_profile():
        yield


@pytest.fixture(scope="function", autouse=True)
def setup_faker():
    Faker.seed(0)
