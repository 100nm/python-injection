from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from injection import get_instance, singleton


class TestSingleton:
    def test_singleton_with_success(self):
        @singleton
        class SomeInjectable:
            pass

        instance_1 = get_instance(SomeInjectable)
        instance_2 = get_instance(SomeInjectable)
        assert instance_1 is instance_2

    def test_singleton_with_recipe(self):
        class SomeClass:
            pass

        @singleton
        def recipe() -> SomeClass:
            return SomeClass()

        instance_1 = get_instance(SomeClass)
        instance_2 = get_instance(SomeClass)
        assert instance_1 is instance_2

    def test_injectable_with_recipe_and_union(self):
        class A:
            pass

        class B(A):
            pass

        @singleton
        def recipe() -> A | B:
            return B()

        a = get_instance(A)
        b = get_instance(B)
        assert a is b
        assert isinstance(a, B)

    def test_singleton_with_recipe_and_no_return_type(self):
        class SomeClass:
            pass

        @singleton
        def recipe():
            return SomeClass()  # pragma: no cover

        assert get_instance(SomeClass) is None

    def test_singleton_with_on(self):
        class A:
            pass

        @singleton(on=A)
        class B(A):
            pass

        a = get_instance(A)
        assert isinstance(a, B)

    def test_singleton_with_on_and_several_classes(self):
        class A:
            pass

        class B(A):
            pass

        @singleton(on=(A, B))
        class C(B):
            pass

        a = get_instance(A)
        b = get_instance(B)
        assert isinstance(a, C)
        assert isinstance(b, C)
        assert a is b

    def test_singleton_with_inject(self):
        @singleton
        class A:
            pass

        @singleton
        class B:
            def __init__(self, __a: A):
                self.a = __a

        a = get_instance(A)
        b = get_instance(B)
        assert isinstance(a, A)
        assert isinstance(b, B)
        assert isinstance(b.a, A)
        assert a is b.a

    def test_singleton_with_dataclass_and_inject(self):
        @singleton
        class A:
            pass

        @singleton
        @dataclass(frozen=True, slots=True)
        class B:
            a: A

        a = get_instance(A)
        b = get_instance(B)
        assert isinstance(a, A)
        assert isinstance(b, B)
        assert isinstance(b.a, A)
        assert a is b.a

    def test_singleton_with_pydantic_model_and_inject(self):
        @singleton
        class A(BaseModel):
            pass

        @singleton
        class B(BaseModel):
            a: A

        a = get_instance(A)
        b = get_instance(B)
        assert isinstance(a, A)
        assert isinstance(b, B)
        assert isinstance(b.a, A)
        assert a is b.a

    def test_singleton_with_recipe_and_inject(self):
        @singleton
        class A:
            pass

        class B:
            pass

        @singleton
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
            pass

        @singleton(on=A)
        class B(A):
            pass

        with pytest.raises(RuntimeError):

            @singleton(on=A)
            class C(A):
                pass

    def test_injectable_with_override(self):
        @singleton
        class A:
            pass

        @singleton(on=A, mode="override")
        class B(A):
            pass

        a = get_instance(A)
        assert isinstance(a, B)
