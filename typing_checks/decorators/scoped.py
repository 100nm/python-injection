from injection import scoped


@scoped("my_scope")
class A:
    def do_a(self) -> None: ...


class AbstractB: ...


@scoped("my_scope", on=AbstractB)
class B(AbstractB):
    def do_b(self) -> None: ...


def function(a: A, b: B) -> None:
    a.do_a()
    b.do_b()
