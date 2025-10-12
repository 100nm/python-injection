from typing import NamedTuple

from injection import asfunction


class TestAsFunction:
    def test_asfunction_with_sync_call_method(self, module):
        @module.injectable
        class Dependency: ...

        @asfunction(module=module)
        class SyncFunction(NamedTuple):
            dependency: Dependency

            def __call__(self):
                return self.dependency

        assert isinstance(SyncFunction(), Dependency)

    async def test_asfunction_with_async_call_method(self, module):
        class Dependency: ...

        @module.injectable
        async def dependency_recipe() -> Dependency:
            return Dependency()

        @asfunction(module=module)
        class AsyncFunction(NamedTuple):
            dependency: Dependency

            async def __call__(self):
                return self.dependency

        assert isinstance(await AsyncFunction(), Dependency)
