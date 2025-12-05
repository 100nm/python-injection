from injection.ext.fastapi import Inject


class A:
    def do(self) -> None: ...


def function(a: Inject[A]) -> None:
    a.do()
