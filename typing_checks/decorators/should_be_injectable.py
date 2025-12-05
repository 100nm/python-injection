from injection import should_be_injectable


@should_be_injectable
class A:
    def do_a(self) -> None: ...


@should_be_injectable()
class B:
    def do_b(self) -> None: ...


def function(a: A, b: B) -> None:
    a.do_a()
    b.do_b()
