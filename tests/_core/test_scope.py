from contextvars import Context

import pytest

from injection._core.scope import adefine_scope, define_scope, get_first_scope
from injection._core.slots import SlotKey
from injection.exceptions import (
    InjectionError,
    ScopeAlreadyDefinedError,
    ScopeError,
    ScopeUndefinedError,
)


def _is_request_scope_defined() -> bool:
    return get_first_scope("request", default=None) is not None


def test_define_scope_with_defined_scope_raises_scope_already_defined_error() -> None:
    with define_scope("request"), pytest.raises(ScopeAlreadyDefinedError):  # noqa: SIM117
        with define_scope("request", kind="shared"):
            pass


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("contextual", False),
        ("shared", True),
    ],
)
def test_define_scope_with_kind(expected: bool, kind: str) -> None:
    with define_scope("request", kind=kind):
        is_defined = Context().run(_is_request_scope_defined)

    assert is_defined is expected


async def test_adefine_scope_with_defined_scope_raises_scope_already_defined_error() -> (
    None
):
    async with adefine_scope("request"):
        with pytest.raises(ScopeAlreadyDefinedError):
            async with adefine_scope("request"):
                pass  # pragma: no cover


def test_get_first_scope_with_defined_scopes_returns_first_defined() -> None:
    with define_scope("session"):
        session = get_first_scope("session")

        with define_scope("request"):
            assert get_first_scope("request", "session") is not session

        assert get_first_scope("request", "session") is session


def test_get_first_scope_without_scope_raises_scope_undefined_error() -> None:
    with pytest.raises(ScopeUndefinedError):
        get_first_scope("request")


def test_get_first_scope_without_scope_returns_default() -> None:
    assert get_first_scope("request", default=None) is None


class TestUserScope:
    def test_set_slot_with_set_slot_raises_injection_error(self) -> None:
        key = SlotKey[object]()

        with define_scope("request") as scope:
            scope.set_slot(key, object())

            with pytest.raises(InjectionError):
                scope.set_slot(key, object())

    def test_set_slot_with_exited_scope_raises_scope_error(self) -> None:
        with define_scope("request") as scope:
            pass

        with pytest.raises(ScopeError):
            scope.set_slot(SlotKey(), object())
