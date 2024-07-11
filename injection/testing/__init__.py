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


testing_mod = partial(mod, "testing")

set_test_constant = testing_mod().set_constant
should_be_test_injectable = testing_mod().should_be_injectable
test_injectable = testing_mod().injectable
test_singleton = testing_mod().singleton


@contextmanager
def use_test_injectables(*, on: Module = None, test_module: Module = None):
    on = on or mod()
    test_module = test_module or testing_mod()

    for module in (on, test_module):
        module.unlock()

    del module

    with on.use_temporarily(test_module, priority=ModulePriority.HIGH):
        yield
        on.unlock()
