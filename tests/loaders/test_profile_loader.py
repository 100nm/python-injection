from dataclasses import dataclass
from uuid import uuid4

import pytest

from injection import find_instance, injectable, mod
from injection.loaders import ProfileLoader


class TestProfileLoader:
    def test_required_module_names_with_success_return_frozenset(self):
        loader = ProfileLoader(
            {
                mod().name: ["a", "b", "c"],
                "dev": ["m", "n", "o"],
                "b": ["x", "y", "z"],
                "c": ["i", "j"],
            }
        )
        assert loader.required_module_names() == {
            mod().name,
            "a",
            "b",
            "c",
            "x",
            "y",
            "z",
            "i",
            "j",
        }

    def test_required_module_names_with_name_return_frozenset(self):
        loader = ProfileLoader(
            {
                mod().name: ["a"],
                "dev": ["z"],
                "test": ["i"],
            }
        )
        assert loader.required_module_names("dev") == {
            mod().name,
            "dev",
            "a",
            "z",
        }

    def test_load_with_success(self):
        profile_name = "test"
        global_profile_name = uuid4().hex

        @mod(global_profile_name).constant
        class GlobalConfig: ...

        @injectable
        @dataclass
        class A:
            config: GlobalConfig

        @mod(profile_name).injectable(on=A)
        class B(A): ...

        loader = ProfileLoader(
            {
                mod().name: [global_profile_name],
                profile_name: [global_profile_name],
            }
        )

        with pytest.raises(TypeError):
            find_instance(A)

        loader.init()

        assert type(find_instance(A)) is A
        loaded_profile = loader.load(profile_name)
        assert type(find_instance(A)) is B

        # Cleaning
        loaded_profile.unload()

    def test_load_with_context_manager(self):
        profile_name = "test"
        global_profile_name = uuid4().hex

        @mod(global_profile_name).constant
        class GlobalConfig: ...

        @injectable
        @dataclass
        class A:
            config: GlobalConfig

        @mod(profile_name).injectable(on=A)
        class B(A): ...

        loader = ProfileLoader(
            {
                mod().name: [global_profile_name],
                profile_name: [global_profile_name],
            }
        )
        loader.init()

        assert type(find_instance(A)) is A

        with loader.load(profile_name):
            assert type(find_instance(A)) is B

        assert type(find_instance(A)) is A
