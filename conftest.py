import logging

import pytest

from injection import Module, mod
from injection._core import Module as CoreModule
from tests.helpers import EventHistory

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(scope="function", autouse=True)
def unlock():
    yield
    mod().unlock()


@pytest.fixture(scope="function")
def module() -> Module | CoreModule:
    return CoreModule()


@pytest.fixture(scope="function")
def event_history(module) -> EventHistory:
    history = EventHistory()
    module.add_listener(history)
    return history
