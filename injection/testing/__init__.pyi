from contextlib import ContextDecorator
from typing import ContextManager

import injection as _
from injection import Module

set_test_constant = _.set_constant
should_be_test_injectable = _.should_be_injectable
test_injectable = _.injectable
test_singleton = _.singleton

def use_test_injectables(
    *,
    module: Module = ...,
    test_module: Module = ...,
) -> ContextManager | ContextDecorator:
    """
    Context manager or decorator for temporary use test module.
    """
