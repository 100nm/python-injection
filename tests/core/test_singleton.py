from dataclasses import dataclass

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

        a = get_instance(A)
        assert isinstance(a, B)

    def test_singleton_with_references(self):
        class A:
            ...

        class B(A):
            ...

        @singleton(references=(A, B))
        class C(B):
            ...

        a = get_instance(A)
        b = get_instance(B)
        assert isinstance(a, C)
        assert isinstance(b, C)
        assert a is b

    def test_injectable_without_auto_inject_raise_type_error(self):
        @singleton
        class A:
            ...

        @singleton(auto_inject=False)
        class B:
            def __init__(self, a: A):
                raise NotImplementedError

        with pytest.raises(TypeError):
            get_instance(B)

    def test_singleton_with_auto_inject(self):
        @singleton
        class A:
            ...

        @singleton(auto_inject=True)
        class B:
            def __init__(self, __a: A):
                self.a = __a

        a = get_instance(A)
        b = get_instance(B)
        assert isinstance(a, A)
        assert isinstance(b, B)
        assert isinstance(b.a, A)
        assert a is b.a

    def test_singleton_with_dataclass_and_auto_inject(self):
        @singleton
        class A:
            ...

        @singleton(auto_inject=True)
        @dataclass(frozen=True, slots=True)
        class B:
            a: A

        a = get_instance(A)
        b = get_instance(B)
        assert isinstance(a, A)
        assert isinstance(b, B)
        assert isinstance(b.a, A)
        assert a is b.a

    def test_singleton_with_recipe_and_auto_inject(self):
        @singleton
        class A:
            ...

        class B:
            ...

        @singleton(reference=B, auto_inject=True)
        def recipe(__a: A) -> B:
            assert isinstance(__a, A)
            assert __a is a
            return B()

        a = get_instance(A)
        b = get_instance(B)
        assert isinstance(a, A)
        assert isinstance(b, B)

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
