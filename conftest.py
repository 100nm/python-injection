import pytest

from injection import Module, default_module
from tests.helpers import EventHistory


@pytest.fixture(scope="function", autouse=True)
def unlock():
    yield
    default_module.unlock()


@pytest.fixture(scope="function")
def module() -> Module:
    return Module(f"{__name__}:test_module")


@pytest.fixture(scope="function")
def event_history(module) -> EventHistory:
    history = EventHistory()
    module.add_listener(history)
    return history
