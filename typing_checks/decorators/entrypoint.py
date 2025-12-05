from injection.entrypoint import Entrypoint, entrypointmaker


class A: ...


@entrypointmaker
def entrypoint[**P, T](ep: Entrypoint[P, T], a: A) -> Entrypoint[P, T]:
    return ep.inject()


@entrypoint
def function_a() -> None: ...


function_a()


@entrypoint()
def function_b() -> None: ...


function_b()


@entrypointmaker()
def _ep[**P, T](ep: Entrypoint[P, T], a: A) -> Entrypoint[P, T]:
    return ep.inject()
