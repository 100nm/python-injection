import pytest

from injection import aget_instance, constant, get_instance


class TestConstant:
    def test_constant_with_success(self):
        @constant
        class SomeInjectable: ...

        instance_1 = get_instance(SomeInjectable)
        instance_2 = get_instance(SomeInjectable)
        assert instance_1 is instance_2 is not None

    def test_constant_with_recipe(self):
        class SomeClass: ...

        @constant
        def recipe() -> SomeClass:
            return SomeClass()

        instance_1 = get_instance(SomeClass)
        instance_2 = get_instance(SomeClass)
        assert instance_1 is instance_2
        assert isinstance(instance_1, SomeClass)

    async def test_constant_with_async_recipe(self):
        class SomeClass: ...

        @constant
        async def recipe() -> SomeClass:
            return SomeClass()

        with pytest.raises(RuntimeError):
            get_instance(SomeClass)

        instance_1 = await aget_instance(SomeClass)
        instance_2 = await aget_instance(SomeClass)
        assert instance_1 is instance_2
        assert isinstance(instance_1, SomeClass)

    def test_constant_with_on(self):
        class A: ...

        @constant(on=A)
        class B(A): ...

        a = get_instance(A)
        assert isinstance(a, B)

    def test_constant_with_on_and_several_classes(self):
        class A: ...

        class B(A): ...

        @constant(on=(A, B))
        class C(B): ...

        a = get_instance(A)
        b = get_instance(B)
        assert isinstance(a, C)
        assert isinstance(b, C)
        assert a is b

    def test_constant_with_injectable_already_exist_raise_runtime_error(self):
        class A: ...

        @constant(on=A)
        class B(A): ...

        with pytest.raises(RuntimeError):

            @constant(on=A)
            class C(A): ...

    def test_constant_with_override(self):
        @constant
        class A: ...

        @constant(on=A, mode="override")
        class B(A): ...

        a = get_instance(A)
        assert isinstance(a, B)

    def test_constant_with_multiple_override(self):
        @constant
        class A: ...

        @constant(on=A, mode="override")
        class B(A): ...

        @constant(on=A, mode="override")
        class C(B): ...

        a = get_instance(A)
        assert isinstance(a, C)
