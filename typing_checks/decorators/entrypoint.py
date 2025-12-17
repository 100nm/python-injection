from injection import adefine_scope
from injection.entrypoint import AsyncEntrypoint, Entrypoint, entrypointmaker


class A: ...


@entrypointmaker
def entrypoint[**P, T](ep: AsyncEntrypoint[P, T], a: A) -> Entrypoint[P, T]:
    return (
        ep.inject().decorate(adefine_scope("lifespan", kind="shared")).async_to_sync()
    )


@entrypoint
async def function_a() -> None: ...


function_a()


@entrypoint()
async def function_b() -> None: ...


function_b()


@entrypointmaker()
def _ep[**P, T](ep: Entrypoint[P, T], a: A) -> Entrypoint[P, T]:
    return ep.inject()
