from injection import find_instance, injectable, mod
from injection.loaders import load_profile


class TestLoadProfile:
    def test_load_profile_with_success(self):
        profile_name = "test"

        @injectable
        class A: ...

        @mod(profile_name).injectable(on=A)
        class B(A): ...

        assert type(find_instance(A)) is A
        load_profile(profile_name)
        assert type(find_instance(A)) is B

        # Cleaning
        mod().init_modules()

    def test_load_profile_with_context_manager(self):
        profile_name = "test"

        @injectable
        class A: ...

        @mod(profile_name).injectable(on=A)
        class B(A): ...

        assert type(find_instance(A)) is A

        with load_profile(profile_name):
            assert type(find_instance(A)) is B

        assert type(find_instance(A)) is A
