from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest

from injection import inject, injectable

T = TypeVar("T")


@injectable
class SomeGenericInjectable(Generic[T]):
    ...


@injectable
class SomeInjectable:
    ...


class SomeClass:
    ...


class TestInject:
    def test_inject_with_success(self):
        @inject
        def my_function(instance: SomeInjectable):
            assert isinstance(instance, SomeInjectable)

        my_function()

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

    def test_inject_with_no_injectable_raise_type_error(self):
        @inject
        def my_function(instance: SomeClass):
            raise NotImplementedError

        with pytest.raises(TypeError):
            my_function()
