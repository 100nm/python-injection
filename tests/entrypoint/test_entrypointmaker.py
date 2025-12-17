from contextlib import contextmanager

from injection.entrypoint import Entrypoint, entrypointmaker


def test_entrypointmaker_with_success_return_entrypoint_decorator():
    count = 0

    @contextmanager
    def increment():
        nonlocal count
        count += 1
        yield

    @entrypointmaker
    def entrypoint[**P, T](self: Entrypoint[P, T]) -> Entrypoint[P, T]:
        return self.decorate(increment())

    @entrypoint
    def function(): ...

    function()
    assert count == 1


def test_entrypointmaker_with_autocall_return_entrypoint_decorator():
    count = 0

    @contextmanager
    def increment():
        nonlocal count
        count += 1
        yield

    @entrypointmaker
    def entrypoint[**P, T](self: Entrypoint[P, T]) -> Entrypoint[P, T]:
        return self.decorate(increment())

    @entrypoint(autocall=True)
    def _(): ...

    assert count == 1
