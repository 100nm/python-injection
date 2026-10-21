from typing import NamedTuple

from injection._core.asfunction import asfunction
from injection._core.module import Module


class A: ...


def test_asfunction_with_sync_call_method_returns_function(module: Module) -> None:
    module.injectable(A)

    @asfunction(module=module)
    class GetA(NamedTuple):
        a: A

        def __call__(self, suffix: str) -> tuple[A, str]:
            return self.a, suffix

    a, suffix = GetA("suffix")

    assert isinstance(a, A)
    assert suffix == "suffix"
    assert GetA.__name__ == "GetA"


async def test_asfunction_with_async_call_method_returns_coroutine_function(
    module: Module,
) -> None:
    @module.injectable
    async def recipe() -> A:
        return A()

    @asfunction(module=module)
    class GetA(NamedTuple):
        a: A

        async def __call__(self) -> A:
            return self.a

    assert isinstance(await GetA(), A)
