from typing import Final

from injection import Module
from injection.loaders import LoadedProfile, ProfileLoader

TEST_PROFILE_NAME: Final[str] = ...

_test_module: Final[Module] = ...

reserve_scoped_test_slot = _test_module.reserve_scoped_slot
set_test_constant = _test_module.set_constant
should_be_test_injectable = _test_module.should_be_injectable
test_constant = _test_module.constant
test_injectable = _test_module.injectable
test_scoped = _test_module.scoped
test_singleton = _test_module.singleton

def load_test_profile(loader: ProfileLoader = ...) -> LoadedProfile:
    """
    Context manager for temporary use test module.
    """
