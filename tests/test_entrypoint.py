from collections.abc import Iterator
from contextlib import contextmanager

from injection._core.module import Module, mod
from injection.entrypoint import Entrypoint, EntrypointBuilder, entrypointmaker
from injection.loaders import ProfileLoader, PythonModuleLoader


class A: ...


class B(A): ...


def test_entrypointmaker_with_setup_method_returns_decorator(module: Module) -> None:
    module.injectable(A)
    steps: list[str] = []

    @contextmanager
    def track() -> Iterator[None]:
        steps.append("enter")
        yield
        steps.append("exit")

    @entrypointmaker(profile_loader=ProfileLoader(module=module))
    def entrypoint[**P, T](self: Entrypoint[P, T], a: A) -> Entrypoint[P, T]:
        steps.append(type(a).__name__)
        return self.decorate(track())

    @entrypoint(autocall=True)
    def main() -> None:
        steps.append("main")

    assert steps == ["A", "enter", "main", "exit"]


class TestEntrypointBuilder:
    def test_async_to_sync_with_success_returns_builder(self) -> None:
        @EntrypointBuilder().async_to_sync()
        async def main() -> int:
            return 42

        assert main() == 42

    def test_inject_with_success_returns_builder(self, module: Module) -> None:
        module.injectable(A)

        @EntrypointBuilder(ProfileLoader(module=module)).inject()
        def main(a: A) -> A:
            return a

        assert isinstance(main(), A)

    def test_load_modules_with_success_returns_builder(self) -> None:
        loader = PythonModuleLoader(lambda name: name.endswith("module1"))

        @EntrypointBuilder().load_modules(loader, "tests.packages.package1")
        def main() -> None:
            return None

        main()

        assert loader.modules.keys() == {"tests.packages.package1.module1"}

    def test_load_profile_with_success_returns_builder(self) -> None:
        root = Module("root")
        root.injectable(A)
        mod("entrypoint_load_profile").injectable(on=A)(B)

        @(
            EntrypointBuilder(ProfileLoader(module=root))
            .inject()
            .load_profile("entrypoint_load_profile")
        )
        def main(a: A) -> A:
            return a

        assert isinstance(main(), B)
        assert type(root.find_instance(A)) is A
