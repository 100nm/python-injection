from typing import ContextManager

import injection as _

set_test_constant = _.set_constant
should_be_test_injectable = _.should_be_injectable
test_constant = _.constant
test_injectable = _.injectable
test_singleton = _.singleton

def load_test_profile(*other_profile_names: str) -> ContextManager[None]:
    """
    Context manager or decorator for temporary use test module.
    """
