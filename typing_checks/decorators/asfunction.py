from typing import NamedTuple

from injection import asfunction


class A: ...


class B: ...


# TODO: idk why mypy check fail here


@asfunction
class FunctionA(NamedTuple):
    a: A
    b: B

    def __call__(self, foo: str) -> None: ...


FunctionA("foo")  # type: ignore[arg-type, call-arg]


@asfunction()
class FunctionB(NamedTuple):
    a: A
    b: B

    def __call__(self, bar: str) -> None: ...


FunctionB("bar")  # type: ignore[arg-type, call-arg]
