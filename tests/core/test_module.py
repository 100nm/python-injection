from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

import pytest

from injection import Module, define_scope
from injection.exceptions import (
    EmptySlotError,
    InjectionError,
    ModuleError,
    ModuleLockError,
    ModuleNotUsedError,
)


class SomeClass: ...


class TestModule:
    """
    __contains__
    """

    def test_contains_with_success_return_bool(self, module):
        class A: ...

        class B: ...

        module.set_constant(A())

        assert A in module
        assert B not in module

    def test_contains_with_union_return_bool(self, module):
        class T: ...

        module.set_constant(T())

        assert T | None in module
        assert str | None not in module

    """
    all_ready
    """

    async def test_all_ready_with_success(self, module):
        class T: ...

        @module.singleton
        async def t_recipe() -> T:
            return T()

        with pytest.raises(RuntimeError):
            module.get_instance(T)

        await module.all_ready()
        instance = module.get_instance(T)
        assert isinstance(instance, T)

    """
    make_async_factory
    """

    async def test_make_async_factory_with_success(self, module):
        class Dependency: ...

        @module.injectable
        async def dependency_recipe() -> Dependency:
            return Dependency()

        @dataclass
        class InnerClass:
            dependency: Dependency

        async_factory = module.make_async_factory(InnerClass)
        instance = await async_factory()

        assert isinstance(instance, InnerClass)
        assert isinstance(instance.dependency, Dependency)

    """
    aget_instance
    """

    async def test_aget_instance_with_success_return_instance(self, module):
        module.set_constant(SomeClass())

        instance = await module.aget_instance(SomeClass)
        assert isinstance(instance, SomeClass)

    async def test_aget_instance_with_no_injectable_return_not_implemented(
        self,
        module,
    ):
        instance = await module.aget_instance(SomeClass)
        assert instance is NotImplemented

    async def test_aget_instance_with_empty_annotated_return_not_implemented(
        self,
        module,
    ):
        instance = await module.aget_instance(Annotated)
        assert instance is NotImplemented

    """
    get_instance
    """

    def test_get_instance_with_success_return_instance(self, module):
        module.set_constant(SomeClass())

        instance = module.get_instance(SomeClass)
        assert isinstance(instance, SomeClass)

    def test_get_instance_with_no_injectable_return_not_implemented(self, module):
        instance = module.get_instance(SomeClass)
        assert instance is NotImplemented

    def test_get_instance_with_empty_annotated_return_not_implemented(self, module):
        instance = module.get_instance(Annotated)
        assert instance is NotImplemented

    """
    aget_lazy_instance
    """

    async def test_aget_lazy_instance_with_success_return_lazy_instance(self, module):
        @module.injectable
        class A: ...

        lazy_instance = module.aget_lazy_instance(A)
        instance1 = await lazy_instance
        instance2 = await lazy_instance
        assert isinstance(instance1, A)
        assert isinstance(instance2, A)
        assert instance1 is not instance2

    async def test_aget_lazy_instance_with_no_injectable_return_lazy_not_implemented(
        self, module
    ):
        lazy_instance = module.aget_lazy_instance(SomeClass)
        assert await lazy_instance is NotImplemented

    """
    get_lazy_instance
    """

    def test_get_lazy_instance_with_success_return_lazy_instance(self, module):
        @module.injectable
        class A: ...

        lazy_instance = module.get_lazy_instance(A)
        instance1 = ~lazy_instance
        instance2 = ~lazy_instance
        assert isinstance(instance1, A)
        assert isinstance(instance2, A)
        assert instance1 is not instance2

    def test_get_lazy_instance_with_no_injectable_return_lazy_not_implemented(
        self, module
    ):
        lazy_instance = module.get_lazy_instance(SomeClass)
        assert ~lazy_instance is NotImplemented

    """
    set_constant
    """

    def test_set_constant_with_success(self, module):
        instance = SomeClass()
        module.set_constant(instance)
        assert instance is module.get_instance(SomeClass)

    def test_set_constant_with_on(self, module):
        class A: ...

        class B(A): ...

        class C(B): ...

        instance = C()
        module.set_constant(instance, on=(A, B))
        assert (
            instance
            is module.get_instance(A)
            is module.get_instance(B)
            is module.get_instance(C)
        )

    def test_set_constant_with_type_alias(self, module):
        type HelloWorld = str
        value = "Hello world!"

        module.set_constant(value, HelloWorld, alias=True)

        assert module.get_instance(str) is NotImplemented
        assert module.get_instance(HelloWorld) is value

    def test_set_constant_with_alias_and_no_on_raise_value_error(self, module):
        value = "Hello world!"

        with pytest.raises(ValueError):
            module.set_constant(value, alias=True)

    """
    reserve_scoped_slot
    """

    def test_reserve_scoped_slot_with_success(self, module):
        scope_name = "test"
        slot_key = module.reserve_scoped_slot(SomeClass, scope_name)

        with define_scope(scope_name) as scope:
            instance = SomeClass()
            scope.set_slot(slot_key, instance)

            assert module.get_instance(SomeClass) is instance

        assert module.get_instance(SomeClass) is NotImplemented

    def test_reserve_scoped_slot_with_empty_raise_empty_slot_error(self, module):
        scope_name = "test"
        module.reserve_scoped_slot(SomeClass, scope_name)

        with define_scope(scope_name):
            with pytest.raises(EmptySlotError):
                module.find_instance(SomeClass)

    def test_reserve_scoped_slot_with_several_definitions_raise_injection_error(
        self,
        module,
    ):
        scope_name = "test"
        slot_key = module.reserve_scoped_slot(SomeClass, scope_name)

        with define_scope(scope_name) as scope:
            instance1 = SomeClass()
            scope.set_slot(slot_key, instance1)

            instance2 = SomeClass()

            with pytest.raises(InjectionError):
                scope.set_slot(slot_key, instance2)

    """
    init_modules
    """

    def test_init_modules_with_success(self, module, event_history):
        residual_module = Module()
        module.use(residual_module)
        event_history.clear()

        second_module = Module()
        third_module = Module()

        module.init_modules(second_module, third_module)
        event_history.assert_length(3)

    """
    use
    """

    def test_use_with_success(self, module, event_history):
        second_module = Module()
        third_module = Module()
        fourth_module = Module()

        module.use(second_module)
        second_module.use(third_module)
        third_module.use(fourth_module)

        event_history.assert_length(3)

    def test_use_with_self_raise_module_error(self, module, event_history):
        with pytest.raises(ModuleError):
            module.use(module)

        event_history.assert_length(0)

    def test_use_with_module_already_in_use_raise_module_error(
        self,
        module,
        event_history,
    ):
        second_module = Module()
        module.use(second_module)

        with pytest.raises(ModuleError):
            module.use(second_module)

        event_history.assert_length(1)

    """
    stop_using
    """

    def test_stop_using_with_success(self, module, event_history):
        second_module = Module()

        module.use(second_module)
        module.stop_using(second_module)

        event_history.assert_length(2)

    def test_stop_using_with_unused_module(self, module, event_history):
        second_module = Module()
        module.stop_using(second_module)
        event_history.assert_length(0)

    """
    use_temporarily
    """

    def test_use_temporarily_with_success(self, module, event_history):
        second_module = Module()
        event_history.assert_length(0)

        with module.use_temporarily(second_module):
            event_history.assert_length(1)

        event_history.assert_length(2)

    def test_use_temporarily_with_decorator(self, module, event_history):
        second_module = Module()

        @module.use_temporarily(second_module)
        def some_function():
            event_history.assert_length(1)

        event_history.assert_length(0)
        some_function()
        event_history.assert_length(2)

    def test_use_temporarily_with_unlock(self, module):
        second_module = Module()

        @module.singleton
        class A: ...

        with pytest.raises(ModuleLockError):
            with module.use_temporarily(second_module):
                module.find_instance(A)

        # Cleaning
        module.unlock().stop_using(second_module)

        # Ensure there are no errors
        with module.use_temporarily(second_module, unlock=True):
            module.find_instance(A)

    """
    change_priority
    """

    def test_change_priority_with_success(self, module, event_history):
        second_module = Module()
        third_module = Module()

        @second_module.injectable
        class A: ...

        @third_module.injectable(on=A)
        class B(A): ...

        module.use(second_module)
        module.use(third_module)
        event_history.assert_length(2)

        assert not isinstance(module.get_instance(A), B)

        module.change_priority(third_module, "high")
        event_history.assert_length(3)
        assert isinstance(module.get_instance(A), B)

        module.change_priority(third_module, "low")
        event_history.assert_length(4)
        assert not isinstance(module.get_instance(A), B)

    def test_change_priority_with_module_not_found(self, module, event_history):
        second_module = Module()

        with pytest.raises(ModuleNotUsedError):
            module.change_priority(second_module, "high")

    """
    unlock
    """

    def test_unlock_with_success(self, module):
        second_module = Module()

        @module.singleton
        class A: ...

        @module.singleton
        class B:
            def __init__(self, a: A):
                self.a = a

        @second_module.singleton(on=A)
        class C(A): ...

        b1: B = module.get_instance(B)

        with pytest.raises(ModuleLockError):
            module.use(second_module)

        module.unlock()

        module.use(second_module)
        b2: B = module.get_instance(B)

        assert b1 is not b2
        assert isinstance(b1.a, A)
        assert isinstance(b2.a, C)

    def test_unlock_with_locked_module_in_use(self, module):
        second_module = Module()
        module.use(second_module)

        @module.singleton
        class A: ...

        @second_module.singleton
        class B: ...

        a = module.get_instance(A)
        b = module.get_instance(B)

        module.unlock()
        assert a is not module.get_instance(A)
        assert b is not module.get_instance(B)

    def test_unlock_with_scoped_dependency(self, module):
        @module.scoped("test")
        class Dependency: ...

        assert module.is_locked is False

        with define_scope("test"):
            instance_1 = module.get_instance(Dependency)
            assert module.is_locked is True

            module.unlock()
            assert module.is_locked is False

            instance_2 = module.get_instance(Dependency)
            assert module.is_locked is True

        assert instance_1 is not instance_2
        assert module.is_locked is False

    def test_unlock_with_scoped_cm_recipe(self, module):
        class Dependency: ...

        @module.scoped("test")
        def dependency_recipe() -> Iterator[Dependency]:
            yield Dependency()

        with define_scope("test"):
            module.get_instance(Dependency)

            with pytest.raises(RuntimeError):
                module.unlock()
