from typing import Any

import pytest

from injection._core.injectables import ConstantInjectable
from injection._core.locator import (
    Locator,
    LocatorDependenciesUpdated,
    Mode,
    StaticInjectableBroker,
    Updater,
)
from injection._core.module import Module
from injection.exceptions import NoInjectable
from tests.helpers.event_history import EventHistory


class A: ...


class B: ...


def _updater(instance: A, mode: Mode) -> Updater[A]:
    return Updater(
        classes=(A,),
        broker=StaticInjectableBroker(ConstantInjectable(instance)),
        mode=mode,
    )


class TestLocator:
    def test_request_without_record_raises_no_injectable(
        self,
        module: Module,
    ) -> None:
        with pytest.raises(NoInjectable):
            Locator().request(A, module)

    @pytest.mark.parametrize(
        ("existing", "new"),
        [
            (Mode.FALLBACK, Mode.NORMAL),
            (Mode.FALLBACK, Mode.OVERRIDE),
            (Mode.NORMAL, Mode.OVERRIDE),
            (Mode.OVERRIDE, Mode.OVERRIDE),
        ],
    )
    def test_update_with_stronger_mode_replaces_record(
        self,
        existing: Mode,
        module: Module,
        new: Mode,
    ) -> None:
        locator = Locator().update(_updater(A(), existing))
        instance = A()

        locator.update(_updater(instance, new))

        assert locator.request(A, module).get_instance() is instance

    @pytest.mark.parametrize(
        ("existing", "new"),
        [
            (Mode.NORMAL, Mode.FALLBACK),
            (Mode.OVERRIDE, Mode.FALLBACK),
            (Mode.OVERRIDE, Mode.NORMAL),
        ],
    )
    def test_update_with_weaker_mode_keeps_record(
        self,
        existing: Mode,
        module: Module,
        new: Mode,
    ) -> None:
        instance = A()
        locator = Locator().update(_updater(instance, existing))
        history = EventHistory()
        locator.add_listener(history)

        locator.update(_updater(A(), new))

        assert locator.request(A, module).get_instance() is instance
        assert history.events == ()

    @pytest.mark.parametrize("mode", [Mode.FALLBACK, Mode.NORMAL])
    def test_update_with_same_mode_raises_runtime_error(self, mode: Mode) -> None:
        locator = Locator().update(_updater(A(), mode))

        with pytest.raises(RuntimeError):
            locator.update(_updater(A(), mode))


class TestLocatorDependenciesUpdated:
    @pytest.mark.parametrize(
        ("classes", "expected"),
        [
            ((), "0 dependency have been updated."),
            ((A,), f"1 dependency have been updated: `{A}`."),
            ((A, B), f"2 dependencies have been updated: `{A}`, `{B}`."),
        ],
    )
    def test_str_with_updated_classes_returns_message(
        self, classes: tuple[Any, ...], expected: str
    ) -> None:
        event = LocatorDependenciesUpdated(Locator(), classes, Mode.NORMAL)

        assert str(event) == expected
