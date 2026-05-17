from concurrent.futures.thread import ThreadPoolExecutor
from threading import Thread

import pytest

from injection import SlotKey, define_scope, find_instance, scoped
from injection.exceptions import ScopeAlreadyDefinedError, ScopeError


def test_define_scope_with_already_defined_in_context_raise_scope_already_defined_error():
    with define_scope("test"):
        with pytest.raises(ScopeAlreadyDefinedError):
            with define_scope("test"):
                pass


def test_define_shared_scope_with_success():
    @scoped("test")
    class Dependency: ...

    def assertion() -> None:
        instance = find_instance(Dependency)
        assert isinstance(instance, Dependency)

    with define_scope("test", kind="shared"):
        Thread(target=assertion).run()


def test_define_shared_scope_with_already_contextual_scope_defined_raise_scope_error():
    def assertion() -> None:
        with pytest.raises(ScopeError):
            with define_scope("test", shared=True):
                pass

    with ThreadPoolExecutor() as executor:
        with define_scope("test"):
            executor.submit(assertion)


def test_define_scope_with_sealed_raise_scope_error():
    with define_scope("test") as scope:
        ...

    with pytest.raises(ScopeError):
        scope.set_slot(SlotKey(), object())
