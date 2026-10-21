from collections.abc import Iterator
from unittest.mock import patch

import pytest

from injection._core.module import Module
from injection.loaders import PythonModuleLoader
from tests.helpers.event_history import EventHistory


@pytest.fixture
def event_history(module: Module) -> EventHistory:
    history = EventHistory()
    module.add_listener(history)
    return history


@pytest.fixture
def module() -> Module:
    return Module()


@pytest.fixture(autouse=True, scope="session")
def patch_sys_modules() -> Iterator[None]:
    with patch.object(PythonModuleLoader, "_sys_modules", {}):
        yield
