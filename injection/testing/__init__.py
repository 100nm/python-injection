from contextlib import contextmanager

from injection import Module, ModulePriority

__all__ = (
    "set_test_constant",
    "should_be_test_injectable",
    "test_injectable",
    "test_singleton",
    "use_test_injectables",
)


def get_test_module() -> Module:
    return Module.from_name("testing")


_module = get_test_module()

set_test_constant = _module.set_constant
should_be_test_injectable = _module.should_be_injectable
test_injectable = _module.injectable
test_singleton = _module.singleton

del _module


@contextmanager
def use_test_injectables(*, on: Module = None, test_module: Module = None):
    on = on or Module.default()
    test_module = test_module or get_test_module()

    for module in (on, test_module):
        module.unlock()

    with on.use_temporarily(test_module, priority=ModulePriority.HIGH):
        yield
        on.unlock()
