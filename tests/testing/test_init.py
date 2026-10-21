from injection import testing
from injection._core.module import Module
from injection.loaders import ProfileLoader


class A: ...


class B(A): ...


def test_load_test_profile_with_success_returns_loaded_profile(module: Module) -> None:
    module.injectable(A)
    testing.test_injectable(on=A)(B)

    with testing.load_test_profile(ProfileLoader(module=module)):
        assert type(module.find_instance(A)) is B

    assert type(module.find_instance(A)) is A
