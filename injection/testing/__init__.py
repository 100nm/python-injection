from collections.abc import Iterator
from contextlib import contextmanager

from injection import Module, ModulePriority, mod

__all__ = (
    "set_test_constant",
    "should_be_test_injectable",
    "test_constant",
    "test_injectable",
    "test_singleton",
    "use_test_injectables",
)


def tmod() -> Module:
    return mod("__testing__")


set_test_constant = tmod().set_constant
should_be_test_injectable = tmod().should_be_injectable
test_constant = tmod().constant
test_injectable = tmod().injectable
test_singleton = tmod().singleton


@contextmanager
def use_test_injectables(
    *,
    module: Module | None = None,
    test_module: Module | None = None,
) -> Iterator[None]:
    module = module or mod()
    test_module = test_module or tmod()

    for m in (module, test_module):
        m.unlock()

    del m

    with module.use_temporarily(test_module, priority=ModulePriority.HIGH):
        yield
        module.unlock()
