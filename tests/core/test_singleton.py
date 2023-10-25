import pytest

from injection import get_instance, singleton


class TestSingleton:
    def test_singleton_with_success(self):
        @singleton
        class SomeInjectable:
            ...

        instance_1 = get_instance(SomeInjectable)
        instance_2 = get_instance(SomeInjectable)
        assert instance_1 is instance_2

    def test_singleton_with_recipe(self):
        class SomeClass:
            ...

        @singleton(reference=SomeClass)
        def recipe() -> SomeClass:
            return SomeClass()

        instance_1 = get_instance(SomeClass)
        instance_2 = get_instance(SomeClass)
        assert instance_1 is instance_2

    def test_singleton_with_reference(self):
        class A:
            ...

        @singleton(reference=A)
        class B(A):
            ...

        instance = get_instance(A)
        assert isinstance(instance, B)

    def test_singleton_with_references(self):
        class A:
            ...

        class B(A):
            ...

        @singleton(references=(A, B))
        class C(B):
            ...

        instance_1 = get_instance(A)
        instance_2 = get_instance(B)
        assert isinstance(instance_1, C)
        assert isinstance(instance_2, C)
        assert instance_1 is instance_2

    def test_singleton_with_injectable_already_exist_raise_runtime_error(self):
        class A:
            ...

        @singleton(reference=A)
        class B(A):
            ...

        with pytest.raises(RuntimeError):

            @singleton(reference=A)
            class C(A):
                ...
