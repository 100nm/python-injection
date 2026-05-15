from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass

import pytest

from injection import (
    adefine_scope,
    afind_instance,
    define_scope,
    find_instance,
    injectable,
    scoped,
)
from injection.exceptions import ScopeError, ScopeUndefinedError


class TestScoped:
    def test_scoped_with_success(self):
        @scoped("test")
        class SomeInjectable: ...

        with define_scope("test"):
            instance_1 = find_instance(SomeInjectable)
            instance_2 = find_instance(SomeInjectable)

        assert instance_1 is instance_2

    def test_scoped_with_several_scopes(self):
        @scoped("scope_2", "scope_1")
        class Dependency: ...

        with define_scope("scope_1"):
            d1 = find_instance(Dependency)

            with define_scope("scope_2"):
                d2 = find_instance(Dependency)

            d3 = find_instance(Dependency)

        assert d1 is not d2
        assert d1 is d3

    def test_scoped_with_on(self):
        class A: ...

        @scoped("test", on=A)
        class B(A): ...

        with define_scope("test"):
            a = find_instance(A)
            b = find_instance(B)

        assert a is b

    def test_scoped_with_on_and_several_classes(self):
        class A: ...

        class B(A): ...

        @scoped("test", on=(A, B))
        class C(B): ...

        with define_scope("test"):
            a = find_instance(A)
            b = find_instance(B)
            c = find_instance(C)

        assert a is b is c

    def test_scoped_with_injectable_already_exist_raise_runtime_error(self):
        class A: ...

        @injectable(on=A)
        class B(A): ...

        with pytest.raises(RuntimeError):

            @scoped("test", on=A)
            class C(A): ...

    def test_scoped_with_get_outside_scope_raise_scope_undefined_error(self):
        @scoped("test")
        class SomeInjectable: ...

        with pytest.raises(ScopeUndefinedError):
            find_instance(SomeInjectable)

    def test_scoped_with_override(self):
        @scoped("test")
        class A: ...

        @scoped("test", on=A, mode="override")
        class B(A): ...

        with define_scope("test"):
            a = find_instance(A)

        assert isinstance(a, B)

    def test_scoped_with_multiple_override(self):
        @scoped("test")
        class A: ...

        @scoped("test", on=A, mode="override")
        class B(A): ...

        @scoped("test", on=A, mode="override")
        class C(B): ...

        with define_scope("test"):
            a = find_instance(A)

        assert isinstance(a, C)

    def test_scoped_with_recipe(self):
        class SomeInjectable: ...

        @scoped("test")
        def some_injectable_recipe() -> SomeInjectable:
            return SomeInjectable()

        with define_scope("test"):
            instance_1 = find_instance(SomeInjectable)
            instance_2 = find_instance(SomeInjectable)

        assert instance_1 is instance_2

    async def test_scoped_with_async_recipe(self):
        class SomeInjectable: ...

        @scoped("test")
        async def some_injectable_recipe() -> SomeInjectable:
            return SomeInjectable()

        with define_scope("test"):
            instance_1 = await afind_instance(SomeInjectable)
            instance_2 = await afind_instance(SomeInjectable)

        assert instance_1 is instance_2

    def test_scoped_with_gen_recipe_and_sync_scope(self):
        class SomeInjectable: ...

        @scoped("test")
        def some_injectable_recipe() -> Iterator[SomeInjectable]:
            yield SomeInjectable()

        with define_scope("test"):
            instance_1 = find_instance(SomeInjectable)
            instance_2 = find_instance(SomeInjectable)

        assert instance_1 is instance_2

    async def test_scoped_with_gen_recipe_and_async_scope(self):
        class SomeInjectable: ...

        @scoped("test")
        def some_injectable_recipe() -> Iterator[SomeInjectable]:
            yield SomeInjectable()

        async with adefine_scope("test"):
            instance_1 = await afind_instance(SomeInjectable)
            instance_2 = find_instance(SomeInjectable)

        assert instance_1 is instance_2

    async def test_scoped_with_async_gen_recipe_and_sync_scope_raise_scope_error(
        self,
    ):
        class SomeInjectable: ...

        @scoped("test")
        async def some_injectable_recipe() -> AsyncIterator[SomeInjectable]:
            yield SomeInjectable()  # pragma: no cover

        with define_scope("test"):
            with pytest.raises(ScopeError):
                await afind_instance(SomeInjectable)

    async def test_scoped_with_async_gen_recipe_and_async_scope(self):
        class SomeInjectable: ...

        @scoped("test")
        async def some_injectable_recipe() -> AsyncIterator[SomeInjectable]:
            yield SomeInjectable()

        async with adefine_scope("test"):
            instance_1 = await afind_instance(SomeInjectable)
            instance_2 = await afind_instance(SomeInjectable)

        assert instance_1 is instance_2

    async def test_scoped_with_scope_not_defined(self):
        @scoped("test")
        class A: ...

        @injectable
        @dataclass
        class B:
            a: A | None = None

        # sync
        b = find_instance(B)
        assert b.a is None

        with define_scope("test"):
            b = find_instance(B)

        assert isinstance(b.a, A)

        # async
        b = await afind_instance(B)
        assert b.a is None

        async with adefine_scope("test"):
            b = await afind_instance(B)

        assert isinstance(b.a, A)
