import logging
from collections.abc import Iterator
from unittest.mock import patch

import pytest

from injection import Module, mod
from injection._core.module import Module as CoreModule
from injection.utils import PythonModuleLoader
from tests.helpers import EventHistory

logging.basicConfig(level=logging.DEBUG)


@pytest.fixture(scope="session", autouse=True)
def __patch_sys_modules() -> Iterator[None]:
    with patch.object(PythonModuleLoader, "_sys_modules", {}):
        yield


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
