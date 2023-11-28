from typing import Any

import pytest

from injection import Module, ModulePriorities
from injection.core import Injectable
from injection.exceptions import ModuleError


class SomeClass:
    ...


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

    def test_getitem_with_success_injectable(self, module):
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
        module.use(fourth_module, priority=ModulePriorities.HIGH)
        injectable_z = self.get_test_injectable(SomeClass())
        fourth_module[SomeClass] = injectable_z
        assert module[SomeClass] is injectable_z

    def test_getitem_with_no_item_raise_key_error(self, module):
        with pytest.raises(KeyError):
            module[SomeClass]

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

    """
    use
    """

    def test_use_with_success(self, module, event_history):
        second_module = Module()
        third_module = Module()

        module.use(second_module)
        module.use(third_module, priority=ModulePriorities.HIGH)

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

        module.change_priority(third_module, ModulePriorities.HIGH)
        event_history.assert_length(3)
        assert module[SomeClass] is injectable_y

        module.change_priority(third_module, ModulePriorities.LOW)
        event_history.assert_length(4)
        assert module[SomeClass] is injectable_x

    def test_change_priority_with_module_not_found(self, module, event_history):
        second_module = Module()
        module.change_priority(second_module, ModulePriorities.HIGH)
        event_history.assert_length(0)
