from collections.abc import Iterator
from contextlib import contextmanager

from injection import injectable, mod
from injection.entrypoint import Entrypoint


class TestEntrypoint:
    def test_async_to_sync_with_success_return_entrypoint(self):
        async def async_function() -> int:
            return 42

        entrypoint = Entrypoint(async_function).async_to_sync()
        assert entrypoint() == 42

    def test_decorate_with_success_return_entrypoint(self):
        enter_count = 0
        exit_count = 0

        @contextmanager
        def decorator() -> Iterator[None]:
            nonlocal enter_count, exit_count
            enter_count += 1
            yield
            exit_count += 1

        def function():
            assert enter_count == exit_count + 1

        entrypoint = Entrypoint(function).decorate(decorator())
        entrypoint()
        assert enter_count == exit_count == 1

    def test_inject_with_success_return_entrypoint(self):
        @injectable
        class Service: ...

        def function(service: Service) -> bool:
            return isinstance(service, Service)

        entrypoint = Entrypoint(function).inject()
        assert entrypoint()

    def test_load_profile_with_success_return_entrypoint(self):
        profile_name = "test"

        @mod(profile_name).injectable
        class Service: ...

        def function(service: Service) -> bool:
            return isinstance(service, Service)

        entrypoint = Entrypoint(function).inject().load_profile(profile_name)
        assert entrypoint()

    def test_setup_with_success_return_entrypoint(self):
        count = 0

        def increment() -> None:
            nonlocal count
            count += 1

        def function(): ...

        entrypoint = Entrypoint(function).setup(increment)
        entrypoint()
        assert count == 1

    def test_async_setup_with_success_return_entrypoint(self):
        count = 0

        async def increment() -> None:
            nonlocal count
            count += 1

        async def function(): ...

        entrypoint = Entrypoint(function).async_setup(increment).async_to_sync()
        entrypoint()
        assert count == 1
