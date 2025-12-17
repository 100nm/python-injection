from collections.abc import Iterator
from contextlib import contextmanager

from injection import injectable, mod
from injection.entrypoint import EntrypointBuilder


class TestEntrypoint:
    def test_async_to_sync_with_success_return_entrypoint(self):
        @EntrypointBuilder().async_to_sync()
        async def async_function() -> int:
            return 42

        assert async_function() == 42

    def test_decorate_with_success_return_entrypoint(self):
        enter_count = 0
        exit_count = 0

        @contextmanager
        def decorator() -> Iterator[None]:
            nonlocal enter_count, exit_count
            enter_count += 1
            yield
            exit_count += 1

        @EntrypointBuilder().decorate(decorator())
        def function():
            assert enter_count == exit_count + 1

        function()
        assert enter_count == exit_count == 1

    def test_inject_with_success_return_entrypoint(self):
        @injectable
        class Service: ...

        @EntrypointBuilder().inject()
        def function(service: Service) -> bool:
            return isinstance(service, Service)

        assert function()

    def test_load_profile_with_success_return_entrypoint(self):
        profile_name = "test"

        @mod(profile_name).injectable
        class Service: ...

        @EntrypointBuilder().inject().load_profile(profile_name)
        def function(service: Service) -> bool:
            return isinstance(service, Service)

        assert function()
