import pytest

from injection import get_instance, injectable, should_be_injectable
from injection.exceptions import InjectionError


class TestShouldBeInjectable:
    def test_should_be_injectable_with_success(self):
        @should_be_injectable
        class SomeInjectable: ...

        with pytest.raises(InjectionError):
            get_instance(SomeInjectable)

        @injectable
        def some_injectable_recipe() -> SomeInjectable:
            return SomeInjectable()

        instance = get_instance(SomeInjectable)
        assert isinstance(instance, SomeInjectable)

    def test_should_be_injectable_with_already_injectable(self):
        @injectable
        class SomeInjectable: ...

        should_be_injectable(SomeInjectable)

        instance = get_instance(SomeInjectable)
        assert isinstance(instance, SomeInjectable)
