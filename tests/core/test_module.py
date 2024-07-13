from typing import Annotated, Any

import pytest

from injection.core import Injectable, Module
from injection.exceptions import (
    ModuleError,
    ModuleLockError,
    ModuleNotUsedError,
)


class SomeClass:
    pass


class TestModule:
    @classmethod
    def get_test_injectable(cls, instance: Any) -> Injectable:
        class_ = type(instance)

        class TestInjectable(Injectable[class_]):
            def get_instance(self) -> class_:
                return instance

        return TestInjectable()

    """
    __getitem__
    """

    def test_getitem_with_success_return_injectable(self, module):
        injectable_w = self.get_test_injectable(SomeClass())
        module[SomeClass] = injectable_w
        assert module[SomeClass] is injectable_w

        second_module = Module()
        module.use(second_module)
        injectable_x = self.get_test_injectable(SomeClass())
        second_module[SomeClass] = injectable_x
        assert module[SomeClass] is injectable_x

        third_module = Module()
        module.use(third_module)
        injectable_y = self.get_test_injectable(SomeClass())
        third_module[SomeClass] = injectable_y
        assert module[SomeClass] is injectable_x

        fourth_module = Module()
        module.use(fourth_module, priority="high")
        injectable_z = self.get_test_injectable(SomeClass())
        fourth_module[SomeClass] = injectable_z
        assert module[SomeClass] is injectable_z

    def test_getitem_with_no_item_raise_key_error(self, module):
        with pytest.raises(KeyError):
            module[SomeClass]

    """
    __contains__
    """

    def test_contains_with_success_return_bool(self, module):
        class A:
            pass

        class B:
            pass

        module[A] = self.get_test_injectable(A())

        assert A in module
        assert B not in module

    def test_contains_with_union_return_bool(self, module):
        class T:
            pass

        module[T] = self.get_test_injectable(T())

        assert T | None in module
        assert str | None not in module

    """
    get_instance
    """

    def test_get_instance_with_success_return_instance(self, module):
        module[SomeClass] = self.get_test_injectable(SomeClass())

        instance = module.get_instance(SomeClass)
        assert isinstance(instance, SomeClass)

    def test_get_instance_with_no_injectable_return_none(self, module):
        instance = module.get_instance(SomeClass)
        assert instance is None

    def test_get_instance_with_empty_annotated_return_none(self, module):
        instance = module.get_instance(Annotated)
        assert instance is None

    """
    get_lazy_instance
    """

    def test_get_lazy_instance_with_success_return_lazy_instance(self, module):
        @module.injectable
        class A:
            pass

        lazy_instance = module.get_lazy_instance(A)
        instance1 = ~lazy_instance
        instance2 = ~lazy_instance
        assert isinstance(instance1, A)
        assert isinstance(instance2, A)
        assert instance1 is not instance2

    def test_get_lazy_instance_with_cache_return_lazy_instance(self, module):
        @module.injectable
        class A:
            pass

        lazy_instance = module.get_lazy_instance(A, cache=True)
        instance1 = ~lazy_instance
        instance2 = ~lazy_instance
        assert isinstance(instance1, A)
        assert isinstance(instance2, A)
        assert instance1 is instance2

    def test_get_lazy_instance_with_no_injectable_return_lazy_none(self, module):
        lazy_instance = module.get_lazy_instance(SomeClass)
        assert ~lazy_instance is None

    """
    set_constant
    """

    def test_set_constant_with_success_return_instance(self, module):
        instance = SomeClass()
        module.set_constant(instance)
        assert instance is module.get_instance(SomeClass)

    def test_set_constant_with_on_return_instance(self, module):
        class A:
            pass

        class B(A):
            pass

        class C(B):
            pass

        instance = C()
        module.set_constant(instance, on=(A, B))
        assert (
            instance
            is module.get_instance(A)
            is module.get_instance(B)
            is module.get_instance(C)
        )

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

        module.use(second_module)
        module.use(third_module, priority="high")

        event_history.assert_length(2)

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

    """
    change_priority
    """

    def test_change_priority_with_success(self, module, event_history):
        second_module = Module()
        third_module = Module()

        injectable_x = self.get_test_injectable(SomeClass())
        injectable_y = self.get_test_injectable(SomeClass())

        second_module[SomeClass] = injectable_x
        third_module[SomeClass] = injectable_y

        module.use(second_module)
        module.use(third_module)
        event_history.assert_length(2)

        assert module[SomeClass] is injectable_x

        module.change_priority(third_module, "high")
        event_history.assert_length(3)
        assert module[SomeClass] is injectable_y

        module.change_priority(third_module, "low")
        event_history.assert_length(4)
        assert module[SomeClass] is injectable_x

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
        class A:
            pass

        @module.singleton
        class B:
            def __init__(self, a: A):
                self.a = a

        @second_module.singleton(on=A)
        class C(A):
            pass

        b1: B = module.get_instance(B)

        with pytest.raises(ModuleLockError):
            module.use(second_module)

        module.unlock()

        module.use(second_module)
        b2: B = module.get_instance(B)

        assert b1 is not b2
        assert isinstance(b1.a, A)
        assert isinstance(b2.a, C)
