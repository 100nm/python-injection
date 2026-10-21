from dataclasses import dataclass
from typing import ClassVar

import pytest

from injection._core.descriptors import LazyInstance, MappedScope
from injection._core.module import Module


class A: ...


class B: ...


class TestMappedScope:
    def test_get_with_class_returns_descriptor(self) -> None:
        descriptor = MappedScope("request")

        class Bindings:
            scope = descriptor

        assert Bindings.scope is descriptor

    def test_set_name_with_second_owner_raises_type_error(self) -> None:
        class First:
            scope = MappedScope("request")

        with pytest.raises(TypeError):

            class Second:
                scope = First.scope


class TestBoundMappedScope:
    def test_define_with_values(self, module: Module) -> None:
        @dataclass
        class Bindings:
            a: A
            b: B | None = None

            scope: ClassVar[MappedScope] = MappedScope("request", module)

        a = A()

        with Bindings(a).scope.define():
            assert module.find_instance(A) is a
            assert module.get_instance(B) is NotImplemented

        assert module.get_instance(A) is NotImplemented

    async def test_adefine_with_values(self, module: Module) -> None:
        @dataclass
        class Bindings:
            a: A

            scope: ClassVar[MappedScope] = MappedScope("request", module)

        a = A()

        async with Bindings(a).scope.adefine():
            assert module.find_instance(A) is a

        assert module.get_instance(A) is NotImplemented


class TestLazyInstance:
    def test_get_with_instance_returns_instance(self, module: Module) -> None:
        module.injectable(A)

        class Service:
            a = LazyInstance(A, module=module)

        assert isinstance(Service().a, A)

    def test_get_with_class_returns_descriptor(self, module: Module) -> None:
        descriptor = LazyInstance(A, module=module)

        class Service:
            a = descriptor

        assert Service.a is descriptor

    def test_get_without_injectable_returns_default(self, module: Module) -> None:
        class Service:
            a = LazyInstance(A, None, module=module)

        assert Service().a is None
