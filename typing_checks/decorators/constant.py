from injection import constant


@constant
class A:
    def do_a(self) -> None: ...


class AbstractB: ...


@constant(on=AbstractB)
class B(AbstractB):
    def do_b(self) -> None: ...


def function(a: A, b: B) -> None:
    a.do_a()
    b.do_b()
