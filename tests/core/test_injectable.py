import pytest

from injection import get_instance, injectable


class TestInjectable:
    def test_injectable_with_success(self):
        @injectable
        class SomeInjectable:
            ...

        instance_1 = get_instance(SomeInjectable)
        instance_2 = get_instance(SomeInjectable)
        assert instance_1 is not instance_2

    def test_injectable_with_recipe(self):
        class SomeClass:
            ...

        @injectable(reference=SomeClass)
        def recipe() -> SomeClass:
            return SomeClass()

        instance_1 = get_instance(SomeClass)
        instance_2 = get_instance(SomeClass)
        assert instance_1 is not instance_2

    def test_injectable_with_reference(self):
        class A:
            ...

        @injectable(reference=A)
        class B(A):
            ...

        instance = get_instance(A)
        assert isinstance(instance, B)

    def test_injectable_with_references(self):
        class A:
            ...

        class B(A):
            ...

        @injectable(references=(A, B))
        class C(B):
            ...

        instance_1 = get_instance(A)
        instance_2 = get_instance(B)
        assert isinstance(instance_1, C)
        assert isinstance(instance_2, C)
        assert instance_1 is not instance_2

    def test_injectable_with_injectable_already_exist_raise_runtime_error(self):
        class A:
            ...

        @injectable(reference=A)
        class B(A):
            ...

        with pytest.raises(RuntimeError):

            @injectable(reference=A)
            class C(A):
                ...
