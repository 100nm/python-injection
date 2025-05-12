from injection.entrypoint import Entrypoint, entrypointmaker


def test_entrypointmaker_with_success_return_entrypoint_decorator():
    count = 0

    def increment() -> None:
        nonlocal count
        count += 1

    @entrypointmaker
    def entrypoint[**P, T](self: Entrypoint[P, T]) -> Entrypoint[P, T]:
        return self.setup(increment)

    @entrypoint
    def function(): ...

    function()
    assert count == 1
