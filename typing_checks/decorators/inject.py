from injection import inject


@inject
class A:
    def do_a(self) -> None: ...


@inject()
class B:
    def do_b(self) -> None: ...


@inject
def function_a(a: A = NotImplemented, b: B = NotImplemented) -> None:
    a.do_a()
    b.do_b()


function_a()


@inject()
def function_b(a: A = NotImplemented, b: B = NotImplemented) -> None:
    a.do_a()
    b.do_b()


function_b()
