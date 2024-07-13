from contextlib import contextmanager
from functools import partial

from injection import Module, ModulePriority, mod

__all__ = (
    "set_test_constant",
    "should_be_test_injectable",
    "test_injectable",
    "test_singleton",
    "use_test_injectables",
)


tmod = partial(mod, "testing")

set_test_constant = tmod().set_constant
should_be_test_injectable = tmod().should_be_injectable
test_injectable = tmod().injectable
test_singleton = tmod().singleton


@contextmanager
def use_test_injectables(*, module: Module = None, test_module: Module = None):
    module = module or mod()
    test_module = test_module or tmod()

    for m in (module, test_module):
        m.unlock()

    del m

    with module.use_temporarily(test_module, priority=ModulePriority.HIGH):
        yield
        module.unlock()
