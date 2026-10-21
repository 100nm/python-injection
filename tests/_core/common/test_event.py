from contextlib import AbstractContextManager

from injection._core.common.event import Event, EventChannel, EventListener
from tests.helpers.event_history import EventHistory


class _Event(Event): ...


class _SilentListener(EventListener):
    def on_event(self, event: Event, /) -> AbstractContextManager[None] | None:
        return None


class TestEventChannel:
    def test_dispatch_with_listener_without_context_manager(self) -> None:
        history = EventHistory()
        silent = _SilentListener()
        channel = EventChannel().add_listener(silent).add_listener(history)
        event = _Event()

        with channel.dispatch(event):
            pass

        assert history.events == (event,)

    def test_dispatch_with_removed_listener(self) -> None:
        history = EventHistory()
        channel = EventChannel().add_listener(history).remove_listener(history)

        with channel.dispatch(_Event()):
            pass

        assert history.events == ()
