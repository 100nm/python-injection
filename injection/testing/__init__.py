from typing import Final

from injection import mod
from injection.loaders import LoadedProfile, ProfileLoader, load_profile

__all__ = (
    "TEST_PROFILE_NAME",
    "load_test_profile",
    "reserve_scoped_test_slot",
    "set_test_constant",
    "should_be_test_injectable",
    "test_constant",
    "test_injectable",
    "test_scoped",
    "test_singleton",
)

TEST_PROFILE_NAME: Final[str] = "__testing__"

reserve_scoped_test_slot = mod(TEST_PROFILE_NAME).reserve_scoped_slot
set_test_constant = mod(TEST_PROFILE_NAME).set_constant
should_be_test_injectable = mod(TEST_PROFILE_NAME).should_be_injectable
test_constant = mod(TEST_PROFILE_NAME).constant
test_injectable = mod(TEST_PROFILE_NAME).injectable
test_scoped = mod(TEST_PROFILE_NAME).scoped
test_singleton = mod(TEST_PROFILE_NAME).singleton


def load_test_profile(loader: ProfileLoader | None = None) -> LoadedProfile:
    return load_profile(TEST_PROFILE_NAME, loader)
