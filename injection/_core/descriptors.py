from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Self, get_type_hints

from injection._core.common.invertible import Invertible
from injection._core.common.type import InputType
from injection._core.module import Module, mod
from injection._core.scope import ScopeKind, ScopeKindStr, adefine_scope, define_scope
from injection._core.slots import SlotKey


class MappedScope:
    __slots__ = ("__keys", "__module", "__name", "__owner")

    __keys: Mapping[str, SlotKey[Any]]
    __module: Module
    __name: str
    __owner: type | None

    def __init__(self, name: str, /, module: Module | None = None) -> None:
        self.__module = module or mod()
        self.__name = name
        self.__owner = None

    def __get__(
        self,
        instance: object | None = None,
        owner: type | None = None,
    ) -> Self | BoundMappedScope:
        if instance is None:
            return self

        mapping = self.__mapping_from(instance)
        return BoundMappedScope(self.__name, mapping)

    def __set_name__(self, owner: type, name: str) -> None:
        if self.__owner:
            raise TypeError(f"`{self}` owner is already defined.")

        self.__keys = MappingProxyType(dict(self.__generate_keys(owner, name)))
        self.__owner = owner

    def __generate_keys(
        self,
        cls: type,
        descriptor_name: str,
    ) -> Iterator[tuple[str, SlotKey[Any]]]:
        for name, hint in get_type_hints(cls).items():
            if name == descriptor_name:
                continue

            key = self.__module.reserve_scoped_slot(hint, scope_name=self.__name)
            yield name, key

    def __mapping_from(self, instance: object) -> dict[SlotKey[Any], Any]:
        return {
            key: value
            for name, key in self.__keys.items()
            if (value := getattr(instance, name, None)) is not None
        }


@dataclass(repr=False, eq=False, frozen=True, slots=True)
class BoundMappedScope:
    name: str
    mapping: Mapping[SlotKey[Any], Any]

    @asynccontextmanager
    async def adefine(
        self,
        /,
        kind: ScopeKind | ScopeKindStr = ScopeKind.get_default(),
        threadsafe: bool | None = None,
    ) -> AsyncIterator[None]:
        async with adefine_scope(self.name, kind, threadsafe) as scope:
            if mapping := self.mapping:
                scope.slot_map(mapping)

            yield

    @contextmanager
    def define(
        self,
        /,
        kind: ScopeKind | ScopeKindStr = ScopeKind.get_default(),
        threadsafe: bool | None = None,
    ) -> Iterator[None]:
        with define_scope(self.name, kind, threadsafe) as scope:
            if mapping := self.mapping:
                scope.slot_map(mapping)

            yield


class LazyInstance[T]:
    __slots__ = ("__value",)

    __value: Invertible[T]

    def __init__(
        self,
        cls: InputType[T],
        /,
        default: T = NotImplemented,
        *,
        module: Module | None = None,
        threadsafe: bool | None = None,
    ) -> None:
        module = module or mod()
        self.__value = module.get_lazy_instance(cls, default, threadsafe=threadsafe)

    def __get__(
        self,
        instance: object | None = None,
        owner: type | None = None,
    ) -> Self | T:
        if instance is None:
            return self

        return ~self.__value
