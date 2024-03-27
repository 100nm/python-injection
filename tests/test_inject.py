import sys
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Optional, TypeVar, Union

import pytest

from injection import inject, injectable

T = TypeVar("T")


@injectable
class SomeGenericInjectable(Generic[T]):
    pass


@injectable
class SomeInjectable:
    pass


class SomeClass:
    pass


class TestInject:
    @classmethod
    def assert_inject(cls, annotation: Any):
        @inject
        def my_function(instance: annotation):
            assert isinstance(instance, SomeInjectable)

        my_function()

    def test_inject_with_success(self):
        self.assert_inject(SomeInjectable)

    def test_inject_with_annotated(self):
        self.assert_inject(Annotated[SomeInjectable, "metadata"])

    def test_inject_with_union(self):
        self.assert_inject(Union[T, SomeInjectable])

    def test_inject_with_new_union(self):
        self.assert_inject(T | SomeInjectable)

    def test_inject_with_union_and_none(self):
        self.assert_inject(None | SomeInjectable)

    def test_inject_with_annotated_and_union(self):
        self.assert_inject(Annotated[T | SomeInjectable, "metadata"])

    def test_inject_with_optional(self):
        self.assert_inject(Optional[SomeInjectable])

    def test_inject_with_positional_only_parameter(self):
        @inject
        def my_function(instance: SomeInjectable, /, **kw):
            assert isinstance(instance, SomeInjectable)

        my_function()

    def test_inject_with_keyword_variable(self):
        kwargs = {"key": "value"}

        @inject
        def my_function(instance: SomeInjectable, **kw):
            assert kw == kwargs
            assert isinstance(instance, SomeInjectable)

        my_function(**kwargs)

    def test_inject_with_positional_variable(self):
        arguments = ("value",)

        @inject
        def my_function(*args, instance: SomeInjectable = ...):
            assert args == arguments
            assert isinstance(instance, SomeInjectable)

        my_function(*arguments)

    def test_inject_with_generic_injectable(self):
        @inject
        def my_function(instance: SomeGenericInjectable[str]):
            assert isinstance(instance, SomeGenericInjectable)

        my_function()

    def test_inject_with_class(self):
        @inject
        class Class:
            def __init__(self, some_injectable: SomeInjectable):
                self.injectable = some_injectable

        instance = Class()
        assert isinstance(instance.injectable, SomeInjectable)

    def test_inject_with_dataclass(self):
        @inject
        @dataclass(frozen=True, slots=True)
        class DataClass:
            injectable: SomeInjectable = ...

        instance = DataClass()
        assert isinstance(instance.injectable, SomeInjectable)

    def test_inject_with_register_injectable_after_injected_function(self):
        class LateInjectable:
            pass

        @inject
        def my_function(instance: LateInjectable):
            assert isinstance(instance, LateInjectable)

        with pytest.raises(TypeError):
            my_function()

        @injectable
        def late_injectable_factory() -> LateInjectable:
            return LateInjectable()

        my_function()

    def test_inject_with_str_type_annotation(self):
        @inject
        def my_function(instance: "SomeInjectable"):
            assert isinstance(instance, SomeInjectable)

        my_function()

    def test_inject_with_non_existent_str_type_annotation_raise_type_error(self):
        @inject
        def my_function(instance: "123"):
            raise NotImplementedError

        with pytest.raises(TypeError):
            my_function()

    def test_inject_with_no_injectable_raise_type_error(self):
        @inject
        def my_function(instance: SomeClass):
            raise NotImplementedError

        with pytest.raises(TypeError):
            my_function()

    def test_inject_with_self_injectable(self):
        @injectable
        class A:
            @inject
            def my_method(self, dependency: SomeInjectable):
                assert isinstance(self, A)
                assert isinstance(dependency, SomeInjectable)
                return self

        A.my_method()

        a = A()
        assert a.my_method() is a

    def test_inject_with_class_method(self):
        @injectable
        class A:
            @classmethod
            @inject
            def my_method(cls, dependency: SomeInjectable):
                assert cls is A
                assert isinstance(dependency, SomeInjectable)
                return cls

        A.my_method()

        a = A()
        assert a.my_method() is A

    def test_inject_with_static_method(self):
        @injectable
        class A:
            @staticmethod
            @inject
            def my_method(dependency: SomeInjectable):
                assert isinstance(dependency, SomeInjectable)

        A.my_method()

        a = A()
        assert a.my_method() is None

    def test_inject_with_set_method_in_multiple_class_raise_type_error(self):
        @inject
        def _method(this, _: SomeInjectable = ...):
            return this

        @injectable
        class A:
            method = _method

        expected_exception = TypeError if sys.version_info >= (3, 12) else RuntimeError
        with pytest.raises(expected_exception):

            @injectable
            class B:
                method = _method

        assert isinstance(A.method(), A)

    def test_inject_with_set_method_after_dependency_resolution_raise_type_error(self):
        @inject
        def _method(this=..., _: SomeInjectable = ...):
            return this

        assert _method() is ...

        expected_exception = TypeError if sys.version_info >= (3, 12) else RuntimeError
        with pytest.raises(expected_exception):

            @injectable
            class A:
                method = _method
