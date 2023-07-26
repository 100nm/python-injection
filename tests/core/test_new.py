import pytest

from injection import new
from injection.core import get_instance


class TestNew:
    def test_new_with_success(self):
        @new
        class SomeInjectable:
            ...

        instance_1 = get_instance(SomeInjectable)
        instance_2 = get_instance(SomeInjectable)
        assert instance_1 is not instance_2

    def test_new_with_recipe(self):
        class SomeClass:
            ...

        @new(reference=SomeClass)
        def recipe() -> SomeClass:
            return SomeClass()

        instance_1 = get_instance(SomeClass)
        instance_2 = get_instance(SomeClass)
        assert instance_1 is not instance_2

    def test_new_with_reference(self):
        class A:
            ...

        @new(reference=A)
        class B(A):
            ...

        instance = get_instance(A)
        assert isinstance(instance, B)

    def test_new_with_references(self):
        class A:
            ...

        class B(A):
            ...

        @new(references=(A, B))
        class C(B):
            ...

        instance_1 = get_instance(A)
        instance_2 = get_instance(B)
        assert isinstance(instance_1, C)
        assert isinstance(instance_2, C)
        assert instance_1 is not instance_2

    def test_new_with_injectable_already_exist_raise_runtime_error(self):
        class A:
            ...

        @new(reference=A)
        class B(A):
            ...

        with pytest.raises(RuntimeError):

            @new(reference=A)
            class C(A):
                ...
