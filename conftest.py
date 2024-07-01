import logging

import pytest

from injection.core import Module
from tests.helpers import EventHistory

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(scope="function", autouse=True)
def unlock():
    yield
    Module.default().unlock()


@pytest.fixture(scope="function")
def module() -> Module:
    return Module()


@pytest.fixture(scope="function")
def event_history(module) -> EventHistory:
    history = EventHistory()
    module.add_listener(history)
    return history
