from dataclasses import dataclass

import pytest

from injection import LazyInstance, MappedScope, Scoped, injectable


class _RawData: ...


class TestMappedScope:
    def test_set_name_with_multiple_owner_raise_type_error(self):
        class BindingsA:
            scope = MappedScope("some_scope")

        with pytest.raises(TypeError):

            class BindingsB:
                scope = BindingsA.scope

    async def test_aopen_with_success(self, module):
        @dataclass
        class Bindings:
            data: Scoped[_RawData]

            scope = MappedScope("some_scope", module=module)

        data = _RawData()
        context = Bindings(data)

        assert module.get_instance(_RawData) is NotImplemented

        async with context.scope.adefine():
            assert module.get_instance(_RawData) is data

        assert module.get_instance(_RawData) is NotImplemented

    def test_open_with_success(self, module):
        @dataclass
        class Bindings:
            data: Scoped[_RawData]
            unscoped_data: int

            scope = MappedScope("some_scope", module=module)

        data = _RawData()
        context = Bindings(data, 2)

        assert module.get_instance(_RawData) is NotImplemented

        with context.scope.define():
            assert module.get_instance(_RawData) is data
            assert module.get_instance(int) is NotImplemented

        assert module.get_instance(_RawData) is NotImplemented

    def test_open_with_optional_types(self, module):
        @dataclass
        class Bindings:
            data: Scoped[_RawData | None] = None
            name: Scoped[str | None] = None

            scope = MappedScope("some_scope", module=module)

        data = _RawData()
        context = Bindings(data)

        with context.scope.define():
            assert module.get_instance(_RawData) is data
            assert module.get_instance(str) is NotImplemented


class TestLazyInstance:
    def test_lazy_instance_with_instance_return_t(self):
        @injectable
        class Dependency: ...

        class SomeClass:
            dependency = LazyInstance(Dependency)

        instance = SomeClass()
        assert isinstance(instance.dependency, Dependency)

    def test_lazy_instance_with_class_return_self(self):
        @injectable
        class Dependency: ...

        descriptor = LazyInstance(Dependency)

        class SomeClass:
            dependency = descriptor

        assert SomeClass.dependency is descriptor

    def test_lazy_instance_with_undefined_dependency_return_not_implemented(self):
        class UndefinedDependency: ...

        class SomeClass:
            dependency = LazyInstance(UndefinedDependency)

        instance = SomeClass()
        assert instance.dependency is NotImplemented
