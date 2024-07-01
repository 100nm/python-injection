from contextlib import ContextDecorator
from typing import ContextManager

from injection import Module

_module: Module = ...

set_test_constant = _module.set_constant
should_be_test_injectable = _module.should_be_injectable
test_injectable = _module.injectable
test_singleton = _module.singleton

del _module

def use_test_injectables(
    *,
    on: Module = ...,
    test_module: Module = ...,
) -> ContextManager | ContextDecorator:
    """
    Context manager or decorator for temporary use test module.
    """
