from unittest import TestCase

import pytest

from injection import inject, new


@new
class SomeInjectable:
    ...


class SomeClass:
    ...


class TestInject(TestCase):
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

        my_function(**kwargs)

    def test_inject_with_positional_variable(self):
        arguments = ("value",)

        @inject
        def my_function(*args, instance: SomeInjectable = ...):
            assert args == arguments

        my_function(*arguments)

    def test_inject_with_no_injectable_raise_type_error(self):
        @inject
        def my_function(instance: SomeClass):
            raise NotImplementedError

        with pytest.raises(TypeError):
            my_function()
