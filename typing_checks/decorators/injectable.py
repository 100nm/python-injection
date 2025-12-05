from injection import injectable


@injectable
class A:
    def do_a(self) -> None: ...


class AbstractB: ...


@injectable(on=AbstractB)
class B(AbstractB):
    def do_b(self) -> None: ...


def function(a: A, b: B) -> None:
    a.do_a()
    b.do_b()
