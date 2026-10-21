import logging
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Annotated, Any, Optional, Union

import anyio
import anyio.lowlevel
import pytest
from pydantic import BaseModel

from injection._core.common.event import Event
from injection._core.module import (
    InjectMetadata,
    Module,
    ModuleAdded,
    ModuleEventProxy,
    ModulePriorityUpdated,
    ModuleRemoved,
    Priority,
    mod,
)
from injection._core.scope import adefine_scope, define_scope
from injection.exceptions import (
    EmptySlotError,
    InjectionError,
    ModuleError,
    ModuleLockError,
    ModuleNotUsedError,
    NoInjectable,
    ScopeError,
    ScopeUndefinedError,
)
from tests.helpers.event_history import EventHistory


class A: ...


class B(A): ...


class C(B): ...


class _Event(Event): ...


class TestModule:
    def test_getitem_with_registered_class_returns_injectable(
        self,
        module: Module,
    ) -> None:
        module.injectable(A)

        injectable = module[A]

        assert isinstance(injectable.get_instance(), A)

    def test_getitem_without_injectable_raises_no_injectable(
        self,
        module: Module,
    ) -> None:
        with pytest.raises(NoInjectable) as exc_info:
            module[A]

        assert exc_info.value.cls is A

    @pytest.mark.parametrize("cls", [A, A | None, Annotated[A, "metadata"]])
    def test_contains_with_registered_class_returns_true(
        self,
        cls: Any,
        module: Module,
    ) -> None:
        module.injectable(A)

        assert cls in module

    def test_contains_without_injectable_returns_false(self, module: Module) -> None:
        assert A not in module

    def test_is_locked_with_resolved_singleton_returns_true(
        self,
        module: Module,
    ) -> None:
        module.singleton(A)
        module.find_instance(A)

        assert module.is_locked is True

    def test_is_locked_without_resolved_singleton_returns_false(
        self,
        module: Module,
    ) -> None:
        module.singleton(A)

        assert module.is_locked is False

    def test_injectable_with_class(self, module: Module) -> None:
        module.injectable(A)

        first = module.find_instance(A)
        second = module.find_instance(A)

        assert isinstance(first, A)
        assert first is not second

    def test_injectable_with_recipe(self, module: Module) -> None:
        @module.injectable
        def recipe() -> A:
            return B()

        assert isinstance(module.find_instance(A), B)

    async def test_injectable_with_async_recipe(self, module: Module) -> None:
        @module.injectable
        async def recipe() -> A:
            return B()

        assert isinstance(await module.afind_instance(A), B)

    def test_injectable_with_union_return_type(self, module: Module) -> None:
        @module.injectable
        def recipe() -> A | B:
            return B()

        assert isinstance(module.find_instance(A), B)
        assert isinstance(module.find_instance(B), B)

    def test_injectable_without_return_type(self, module: Module) -> None:
        @module.injectable
        def recipe():
            raise NotImplementedError

        assert A not in module

    @pytest.mark.parametrize("on", [A, (A, B)])
    def test_injectable_with_on(self, module: Module, on: Any) -> None:
        module.injectable(on=on)(C)

        assert isinstance(module.find_instance(A), C)
        assert isinstance(module.find_instance(C), C)

    def test_injectable_with_ignore_type_hint(self, module: Module) -> None:
        module.injectable(ignore_type_hint=True, on=A)(B)

        assert isinstance(module.find_instance(A), B)
        assert B not in module

    def test_injectable_without_inject(self, module: Module) -> None:
        module.injectable(A)

        @module.injectable(inject=False)
        @dataclass
        class Service:
            a: A | None = None

        assert module.find_instance(Service).a is None

    def test_injectable_with_init_dependency(self, module: Module) -> None:
        module.injectable(A)

        @module.injectable
        class Service:
            def __init__(self, a: A) -> None:
                self.a = a

        assert isinstance(module.find_instance(Service).a, A)

    def test_injectable_with_dataclass_dependency(self, module: Module) -> None:
        module.injectable(A)

        @module.injectable
        @dataclass(frozen=True)
        class Service:
            a: A

        assert isinstance(module.find_instance(Service).a, A)

    def test_injectable_with_pydantic_model_dependency(self, module: Module) -> None:
        @module.injectable
        class Dependency(BaseModel): ...

        @module.injectable
        class Service(BaseModel):
            dependency: Dependency

        assert isinstance(module.find_instance(Service).dependency, Dependency)

    def test_injectable_with_recipe_dependency(self, module: Module) -> None:
        module.injectable(A)

        @module.injectable
        def recipe(a: A) -> B:
            assert isinstance(a, A)
            return B()

        assert isinstance(module.find_instance(B), B)

    def test_injectable_with_registered_class_raises_runtime_error(
        self,
        module: Module,
    ) -> None:
        module.injectable(A)

        with pytest.raises(RuntimeError):
            module.injectable(on=A)(B)

    def test_injectable_with_override_mode(self, module: Module) -> None:
        module.injectable(A)

        module.injectable(on=A, mode="override")(B)

        assert isinstance(module.find_instance(A), B)

    def test_injectable_with_generic_class(self, module: Module) -> None:
        @module.injectable
        class Repository[T]: ...

        assert isinstance(module.find_instance(Repository[A]), Repository)

    def test_injectable_with_parameterized_generic_on(self, module: Module) -> None:
        class Factory[T]: ...

        @module.injectable(on=Factory[A])
        class AFactory(Factory[A]): ...

        assert isinstance(module.find_instance(Factory[A]), Factory)
        assert Factory[B] not in module

    def test_singleton_with_class(self, module: Module) -> None:
        module.singleton(A)

        assert module.find_instance(A) is module.find_instance(A)

    async def test_singleton_with_async_recipe(self, module: Module) -> None:
        @module.singleton
        async def recipe() -> A:
            return A()

        instance = await module.afind_instance(A)

        assert module.find_instance(A) is instance

    async def test_singleton_with_concurrent_async_resolutions(
        self,
        module: Module,
    ) -> None:
        @module.singleton
        async def recipe() -> A:
            await anyio.lowlevel.checkpoint()
            return A()

        instances: list[A] = []

        async def append_instance() -> None:
            instances.append(await module.afind_instance(A))

        async with anyio.create_task_group() as task_group:
            for _ in range(10):
                task_group.start_soon(append_instance)

        assert all(instance is instances[0] for instance in instances)

    def test_constant_with_class(self, module: Module) -> None:
        module.constant(A)

        assert module.find_instance(A) is module.find_instance(A)

    def test_constant_without_dependency_injection(self, module: Module) -> None:
        module.injectable(A)

        @module.constant
        @dataclass
        class Settings:
            a: A | None = None

        assert module.find_instance(Settings).a is None

    def test_scoped_with_class(self, module: Module) -> None:
        module.scoped("request")(A)

        with define_scope("request"):
            first = module.find_instance(A)
            second = module.find_instance(A)

        with define_scope("request"):
            third = module.find_instance(A)

        assert first is second
        assert first is not third

    def test_scoped_with_recipe(self, module: Module) -> None:
        @module.scoped("request")
        def recipe() -> A:
            return B()

        with define_scope("request"):
            assert isinstance(module.find_instance(A), B)

    async def test_scoped_with_async_recipe(self, module: Module) -> None:
        @module.scoped("request")
        async def recipe() -> A:
            return B()

        async with adefine_scope("request"):
            assert isinstance(await module.afind_instance(A), B)

    def test_scoped_with_generator_recipe(self, module: Module) -> None:
        steps: list[str] = []

        @module.scoped("request")
        def recipe() -> Iterator[A]:
            steps.append("enter")
            yield A()
            steps.append("exit")

        with define_scope("request"):
            module.find_instance(A)
            assert steps == ["enter"]

        assert steps == ["enter", "exit"]

    async def test_scoped_with_generator_recipe_and_async_scope(
        self,
        module: Module,
    ) -> None:
        @module.scoped("request")
        def recipe() -> Iterator[A]:
            yield A()

        async with adefine_scope("request"):
            instance = await module.afind_instance(A)

            assert module.find_instance(A) is instance

    async def test_scoped_with_async_generator_recipe(self, module: Module) -> None:
        steps: list[str] = []

        @module.scoped("request")
        async def recipe() -> AsyncIterator[A]:
            steps.append("enter")
            yield A()
            steps.append("exit")

        async with adefine_scope("request"):
            instance = await module.afind_instance(A)

            assert await module.afind_instance(A) is instance
            assert steps == ["enter"]

        assert steps == ["enter", "exit"]

    async def test_scoped_with_async_generator_recipe_and_sync_scope_raises_scope_error(
        self,
        module: Module,
    ) -> None:
        @module.scoped("request")
        async def recipe() -> AsyncIterator[A]:
            yield A()  # pragma: no cover

        with define_scope("request"), pytest.raises(ScopeError):
            await module.afind_instance(A)

    def test_scoped_with_async_generator_recipe_and_sync_resolution_raises_runtime_error(
        self,
        module: Module,
    ) -> None:
        @module.scoped("request")
        async def recipe() -> AsyncIterator[A]:
            yield A()  # pragma: no cover

        with define_scope("request"), pytest.raises(RuntimeError):
            module.find_instance(A)

    def test_scoped_with_several_scope_names(self, module: Module) -> None:
        module.scoped("request", "session")(A)

        with define_scope("session"):
            in_session = module.find_instance(A)

            with define_scope("request"):
                in_request = module.find_instance(A)

        assert in_session is not in_request

    def test_scoped_with_ignore_type_hint(self, module: Module) -> None:
        @module.scoped("request", ignore_type_hint=True, on=A)
        def recipe() -> Iterator[B]:
            yield B()

        with define_scope("request"):
            assert isinstance(module.find_instance(A), B)
            assert B not in module

    def test_scoped_without_scope_raises_scope_undefined_error(
        self,
        module: Module,
    ) -> None:
        module.scoped("request")(A)

        with pytest.raises(ScopeUndefinedError):
            module.find_instance(A)

    async def test_scoped_with_optional_dependency_outside_scope(
        self,
        module: Module,
    ) -> None:
        module.scoped("request")(A)

        @module.injectable
        @dataclass
        class Service:
            a: A | None = None

        assert module.find_instance(Service).a is None
        assert (await module.afind_instance(Service)).a is None

    def test_should_be_injectable_without_injectable_raises_injection_error(
        self,
        module: Module,
    ) -> None:
        module.should_be_injectable(A)

        with pytest.raises(InjectionError):
            module.find_instance(A)

    async def test_should_be_injectable_without_injectable_and_async_resolution_raises_injection_error(
        self,
        module: Module,
    ) -> None:
        module.should_be_injectable()(A)

        with pytest.raises(InjectionError):
            await module.afind_instance(A)

    def test_should_be_injectable_with_registered_injectable(
        self,
        module: Module,
    ) -> None:
        module.injectable(on=A)(B)

        module.should_be_injectable(A)

        assert isinstance(module.find_instance(A), B)

    def test_should_be_injectable_with_injectable_registered_after(
        self,
        module: Module,
    ) -> None:
        module.should_be_injectable(A)

        module.injectable(on=A)(B)

        assert isinstance(module.find_instance(A), B)

    def test_set_constant_with_instance_returns_instance(self, module: Module) -> None:
        instance = A()

        constant = module.set_constant(instance)

        assert constant is instance
        assert module.find_instance(A) is instance

    def test_set_constant_with_on(self, module: Module) -> None:
        instance = C()

        module.set_constant(instance, on=A)

        assert module.find_instance(A) is instance
        assert module.find_instance(C) is instance

    def test_set_constant_with_alias(self, module: Module) -> None:
        type Greeting = str

        module.set_constant("Hello", Greeting, alias=True)

        assert module.find_instance(Greeting) == "Hello"
        assert str not in module

    def test_set_constant_with_alias_without_on_raises_value_error(
        self,
        module: Module,
    ) -> None:
        with pytest.raises(ValueError):
            module.set_constant("Hello", alias=True)

    async def test_reserve_scoped_slot_with_set_slot(self, module: Module) -> None:
        key = module.reserve_scoped_slot(A, "request")
        instance = A()

        with define_scope("request") as scope:
            scope.set_slot(key, instance)

            assert module.find_instance(A) is instance
            assert await module.afind_instance(A) is instance

    def test_reserve_scoped_slot_without_set_slot_raises_empty_slot_error(
        self,
        module: Module,
    ) -> None:
        module.reserve_scoped_slot(A, "request")

        with define_scope("request"), pytest.raises(EmptySlotError):
            module.find_instance(A)

    def test_reserve_scoped_slot_without_scope(self, module: Module) -> None:
        module.reserve_scoped_slot(A, "request")

        assert module.get_instance(A) is NotImplemented

    @pytest.mark.parametrize(
        "annotation",
        [
            A,
            "A",
            A | None,
            Optional[A],  # noqa: UP045
            Union[str, A],  # noqa: UP007
            Annotated[A, "metadata"],
        ],
    )
    def test_inject_with_registered_annotation(
        self,
        annotation: Any,
        module: Module,
    ) -> None:
        module.injectable(A)

        @module.inject
        def function(a: annotation) -> A:
            return a

        assert isinstance(function(), A)

    def test_inject_with_explicit_argument(self, module: Module) -> None:
        module.singleton(A)
        instance = A()

        @module.inject
        def function(a: A) -> A:
            return a

        assert function(instance) is instance
        assert module.is_locked is False

    def test_inject_with_variadic_parameters(self, module: Module) -> None:
        module.injectable(A)

        @module.inject
        def function(
            *args: Any,
            a: A = NotImplemented,
            **kwargs: Any,
        ) -> tuple[tuple[Any, ...], A, dict[str, Any]]:
            return args, a, kwargs

        args, a, kwargs = function(1, key="value")

        assert args == (1,)
        assert isinstance(a, A)
        assert kwargs == {"key": "value"}

    def test_inject_with_positional_only_parameter(self, module: Module) -> None:
        module.injectable(A)

        @module.inject
        def function(a: A, /) -> A:
            return a

        assert isinstance(function(), A)

    def test_inject_without_injectable_raises_type_error(self, module: Module) -> None:
        @module.inject
        def function(a: A) -> None:
            raise NotImplementedError

        with pytest.raises(TypeError):
            function()

    def test_inject_with_injectable_registered_after(self, module: Module) -> None:
        @module.inject
        def function(a: A) -> A:
            return a

        with pytest.raises(TypeError):
            function()

        module.injectable(A)

        assert isinstance(function(), A)

    async def test_inject_with_async_function(self, module: Module) -> None:
        @module.injectable
        async def recipe() -> A:
            return A()

        @module.inject
        async def function(a: A) -> A:
            return a

        assert isinstance(await function(), A)

    def test_inject_with_async_dependency_in_sync_function_raises_runtime_error(
        self,
        module: Module,
    ) -> None:
        @module.injectable
        async def recipe() -> A:
            raise NotImplementedError

        @module.inject
        def function(a: A) -> None:
            raise NotImplementedError

        with pytest.raises(RuntimeError):
            function()

    def test_inject_with_class(self, module: Module) -> None:
        module.injectable(A)

        @module.inject
        class Service:
            def __init__(self, a: A) -> None:
                self.a = a

        assert isinstance(Service().a, A)

    def test_inject_with_method(self, module: Module) -> None:
        module.injectable(A)

        @module.injectable
        class Service:
            @module.inject
            def method(self, a: A) -> tuple["Service", A]:
                return self, a

        service = Service()

        assert service.method()[0] is service
        assert isinstance(Service.method()[0], Service)
        assert isinstance(service.method()[1], A)

    def test_inject_with_classmethod(self, module: Module) -> None:
        module.injectable(A)

        class Service:
            @classmethod
            @module.inject
            def method(cls, a: A) -> tuple[type["Service"], A]:
                return cls, a

        cls, a = Service.method()

        assert cls is Service
        assert isinstance(a, A)

    def test_inject_with_staticmethod(self, module: Module) -> None:
        module.injectable(A)

        class Service:
            @staticmethod
            @module.inject
            def method(a: A) -> A:
                return a

        assert isinstance(Service().method(), A)

    def test_inject_with_method_in_several_classes_raises_type_error(
        self,
        module: Module,
    ) -> None:
        @module.inject
        def method(self: Any) -> None:
            raise NotImplementedError

        class First:
            first = method

        with pytest.raises(TypeError):

            class Second:
                second = method

    def test_inject_with_method_set_after_resolution_raises_type_error(
        self,
        module: Module,
    ) -> None:
        @module.inject
        def method(self: Any = None) -> None:
            return None

        method()

        with pytest.raises(TypeError):

            class Service:
                service = method

    async def test_make_async_factory_with_async_dependency_returns_factory(
        self,
        module: Module,
    ) -> None:
        @module.injectable
        async def recipe() -> A:
            return A()

        @dataclass
        class Service:
            a: A

        factory = module.make_async_factory(Service)

        assert isinstance((await factory()).a, A)

    def test_find_instance_with_async_recipe_raises_runtime_error(
        self,
        module: Module,
    ) -> None:
        @module.injectable
        async def recipe() -> A:
            raise NotImplementedError

        with pytest.raises(RuntimeError):
            module.find_instance(A)

    async def test_afind_instance_with_sync_recipe_returns_instance(
        self,
        module: Module,
    ) -> None:
        module.injectable(A)

        assert isinstance(await module.afind_instance(A), A)

    async def test_afind_instance_with_constant_returns_instance(
        self,
        module: Module,
    ) -> None:
        module.constant(A)

        assert await module.afind_instance(A) is module.find_instance(A)

    async def test_afind_instance_with_set_constant_returns_instance(
        self,
        module: Module,
    ) -> None:
        instance = module.set_constant(A())

        assert await module.afind_instance(A) is instance

    async def test_afind_instance_without_injectable_raises_no_injectable(
        self,
        module: Module,
    ) -> None:
        with pytest.raises(NoInjectable):
            await module.afind_instance(A)

    def test_get_instance_with_injectable_returns_instance(
        self,
        module: Module,
    ) -> None:
        module.injectable(A)

        assert isinstance(module.get_instance(A), A)

    @pytest.mark.parametrize(
        ("default", "expected"),
        [
            ({}, NotImplemented),
            ({"default": None}, None),
        ],
    )
    def test_get_instance_without_injectable_returns_default(
        self,
        default: dict[str, Any],
        expected: Any,
        module: Module,
    ) -> None:
        assert module.get_instance(A, **default) is expected

    async def test_aget_instance_with_injectable_returns_instance(
        self,
        module: Module,
    ) -> None:
        module.injectable(A)

        assert isinstance(await module.aget_instance(A), A)

    @pytest.mark.parametrize(
        ("default", "expected"),
        [
            ({}, NotImplemented),
            ({"default": None}, None),
        ],
    )
    async def test_aget_instance_without_injectable_returns_default(
        self,
        default: dict[str, Any],
        expected: Any,
        module: Module,
    ) -> None:
        assert await module.aget_instance(A, **default) is expected

    def test_get_lazy_instance_with_injectable_returns_invertible(
        self,
        module: Module,
    ) -> None:
        lazy_instance = module.get_lazy_instance(A)
        module.injectable(A)

        first = ~lazy_instance
        second = ~lazy_instance

        assert isinstance(first, A)
        assert first is not second

    def test_get_lazy_instance_without_injectable_returns_default(
        self,
        module: Module,
    ) -> None:
        lazy_instance = module.get_lazy_instance(A, None)

        assert ~lazy_instance is None

    async def test_aget_lazy_instance_with_injectable_returns_awaitable(
        self,
        module: Module,
    ) -> None:
        lazy_instance = module.aget_lazy_instance(A)
        module.injectable(A)

        first = await lazy_instance
        second = await lazy_instance

        assert isinstance(first, A)
        assert first is not second

    async def test_aget_lazy_instance_without_injectable_returns_default(
        self,
        module: Module,
    ) -> None:
        lazy_instance = module.aget_lazy_instance(A, None)

        assert await lazy_instance is None

    def test_init_modules_with_used_module(
        self,
        event_history: EventHistory,
        module: Module,
    ) -> None:
        previous, first, second = Module(), Module(), Module()
        module.use(previous)
        event_history.clear()

        module.init_modules(first, second)

        assert event_history.events == (
            ModuleRemoved(module, previous),
            ModuleAdded(module, first, Priority.LOW),
            ModuleAdded(module, second, Priority.LOW),
        )

    def test_use_with_module(self, event_history: EventHistory, module: Module) -> None:
        other = Module()
        other.injectable(A)

        module.use(other)

        assert isinstance(module.find_instance(A), A)
        assert event_history.events == (ModuleAdded(module, other, Priority.LOW),)

    def test_use_with_module_overriding_own_injectable(self, module: Module) -> None:
        other = Module()
        module.injectable(A)
        other.injectable(on=A)(B)

        module.use(other)

        assert isinstance(module.find_instance(A), B)

    @pytest.mark.parametrize(
        ("priority", "expected"),
        [
            (Priority.LOW, B),
            (Priority.HIGH, C),
        ],
    )
    def test_use_with_priority(
        self,
        expected: type[A],
        module: Module,
        priority: Priority,
    ) -> None:
        first, second = Module(), Module()
        first.injectable(on=A)(B)
        second.injectable(on=A)(C)
        module.use(first)

        module.use(second, priority=priority)

        assert type(module.find_instance(A)) is expected

    def test_use_with_itself_raises_module_error(
        self,
        event_history: EventHistory,
        module: Module,
    ) -> None:
        with pytest.raises(ModuleError):
            module.use(module)

        assert event_history.events == ()

    def test_use_with_used_module_raises_module_error(self, module: Module) -> None:
        other = Module()
        module.use(other)

        with pytest.raises(ModuleError):
            module.use(other)

    def test_use_with_locked_module_raises_module_lock_error(
        self,
        module: Module,
    ) -> None:
        module.singleton(A)
        module.find_instance(A)

        with pytest.raises(ModuleLockError):
            module.use(Module())

    def test_stop_using_with_used_module(
        self,
        event_history: EventHistory,
        module: Module,
    ) -> None:
        other = Module()
        other.injectable(A)
        module.use(other)
        event_history.clear()

        module.stop_using(other)

        assert A not in module
        assert event_history.events == (ModuleRemoved(module, other),)

    def test_stop_using_with_unused_module(
        self,
        event_history: EventHistory,
        module: Module,
    ) -> None:
        module.stop_using(Module())

        assert event_history.events == ()

    def test_use_temporarily_with_module(self, module: Module) -> None:
        other = Module()
        other.injectable(A)

        with module.use_temporarily(other):
            assert A in module

        assert A not in module

    def test_use_temporarily_with_resolved_singleton_raises_module_lock_error(
        self,
        module: Module,
    ) -> None:
        other = Module()
        other.singleton(A)

        with pytest.raises(ModuleLockError), module.use_temporarily(other):
            module.find_instance(A)

    def test_use_temporarily_with_unlock(self, module: Module) -> None:
        other = Module()
        other.singleton(A)

        with module.use_temporarily(other, unlock=True):
            module.find_instance(A)

        assert A not in module

    def test_change_priority_with_used_module(
        self,
        event_history: EventHistory,
        module: Module,
    ) -> None:
        first, second = Module(), Module()
        first.injectable(on=A)(B)
        second.injectable(on=A)(C)
        module.use(first).use(second)
        event_history.clear()

        module.change_priority(second, "high")

        assert type(module.find_instance(A)) is C
        assert event_history.events == (
            ModulePriorityUpdated(module, second, Priority.HIGH),
        )

    def test_change_priority_with_unused_module_raises_module_not_used_error(
        self,
        module: Module,
    ) -> None:
        with pytest.raises(ModuleNotUsedError):
            module.change_priority(Module(), "high")

    def test_unlock_with_resolved_singletons(self, module: Module) -> None:
        other = Module()
        module.singleton(A)
        other.singleton(B)
        module.singleton(C)
        module.use(other)
        a = module.find_instance(A)
        b = module.find_instance(B)

        module.unlock()

        assert module.is_locked is False
        assert module.find_instance(A) is not a
        assert module.find_instance(B) is not b

    def test_unlock_with_constant(self, module: Module) -> None:
        instance = module.set_constant(A())

        module.unlock()

        assert module.find_instance(A) is instance

    @pytest.mark.parametrize("kind", ["contextual", "shared"])
    def test_unlock_with_open_scope_raises_runtime_error(
        self,
        kind: Any,
        module: Module,
    ) -> None:
        module.scoped("request")(A)

        with define_scope("request", kind=kind):
            module.find_instance(A)

            with pytest.raises(RuntimeError):
                module.unlock()

    async def test_all_ready_with_requested_async_singleton(
        self,
        module: Module,
    ) -> None:
        @module.singleton
        async def recipe() -> A:
            return A()

        module[A]

        await module.all_ready()

        assert isinstance(module.find_instance(A), A)

    async def test_all_ready_with_resolved_singleton(self, module: Module) -> None:
        module.singleton(A)
        instance = module.find_instance(A)

        await module.all_ready()

        assert module.find_instance(A) is instance

    def test_add_logger_with_logger(
        self,
        caplog: pytest.LogCaptureFixture,
        module: Module,
    ) -> None:
        logger = logging.getLogger("tests")
        caplog.set_level(logging.DEBUG, logger="tests")
        other = Module()

        module.add_logger(logger).use(other)

        assert caplog.messages == [f"`{module}` now uses `{other}`."]

    def test_remove_listener_with_listener(self, module: Module) -> None:
        history = EventHistory()
        module.add_listener(history)

        module.remove_listener(history).use(Module())

        assert history.events == ()

    def test_on_event_with_used_module_event(
        self,
        event_history: EventHistory,
        module: Module,
    ) -> None:
        other, used_by_other = Module(), Module()
        module.use(other)
        event_history.clear()

        other.use(used_by_other)

        origin = ModuleAdded(other, used_by_other, Priority.LOW)
        assert event_history.events == (ModuleEventProxy(module, origin),)

    def test_from_name_with_same_name_returns_same_module(self) -> None:
        assert Module.from_name("tests") is Module.from_name("tests")

    def test_default_with_success_returns_default_module(self) -> None:
        assert Module.default().name == "__default__"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (None, "__default__"),
        ("tests", "tests"),
    ],
)
def test_mod_with_optional_name_returns_named_module(
    expected: str, name: str | None
) -> None:
    module = mod(name)

    assert module.name == expected
    assert mod(name) is module


class TestModuleEventProxy:
    def test_str_with_success_returns_message(self, module: Module) -> None:
        event = _Event()
        proxy = ModuleEventProxy(module, event)

        assert str(proxy) == f"`{module}` has propagated an event: {event}"

    def test_origin_with_nested_proxies_returns_first_event(
        self,
        module: Module,
    ) -> None:
        event = _Event()
        proxy = ModuleEventProxy(module, ModuleEventProxy(Module(), event))

        assert proxy.origin is event


class TestModuleAdded:
    def test_str_with_success_returns_message(self, module: Module) -> None:
        other = Module()

        message = str(ModuleAdded(module, other, Priority.LOW))

        assert message == f"`{module}` now uses `{other}`."


class TestModuleRemoved:
    def test_str_with_success_returns_message(self, module: Module) -> None:
        other = Module()

        message = str(ModuleRemoved(module, other))

        assert message == f"`{module}` no longer uses `{other}`."


class TestModulePriorityUpdated:
    def test_str_with_success_returns_message(self, module: Module) -> None:
        other = Module()

        message = str(ModulePriorityUpdated(module, other, Priority.HIGH))

        assert message == (
            f"In `{module}`, the priority `high` has been applied to `{other}`."
        )


class TestInjectMetadata:
    def test_on_event_without_module_event_returns_none(self) -> None:
        metadata = InjectMetadata(A)

        assert metadata.on_event(_Event()) is None
