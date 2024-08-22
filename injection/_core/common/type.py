from collections.abc import Awaitable, Callable, Iterable, Iterator
from inspect import iscoroutinefunction, isfunction
from types import GenericAlias, UnionType
from typing import (
    Annotated,
    Any,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

type TypeDef[T] = type[T] | TypeAliasType | GenericAlias
type InputType[T] = TypeDef[T] | UnionType
type TypeInfo[T] = InputType[T] | Callable[..., T] | Iterable[TypeInfo[T]]


def get_return_types(*args: TypeInfo[Any]) -> Iterator[InputType[Any]]:
    for arg in args:
        if isinstance(arg, Iterable) and not (
            isinstance(arg, type | str) or isinstance(get_origin(arg), type)
        ):
            inner_args = arg

        elif isfunction(arg) and (return_type := get_type_hints(arg).get("return")):
            if iscoroutinefunction(arg):
                return_type = Awaitable[return_type]  # type: ignore[valid-type]

            inner_args = (return_type,)

        else:
            yield arg  # type: ignore[misc]
            continue

        yield from get_return_types(*inner_args)


def standardize_types(
    *types: InputType[Any],
    with_origin: bool = False,
) -> Iterator[TypeDef[Any]]:
    for tp in types:
        if tp is None:
            continue

        origin = get_origin(tp)

        if origin is Union or isinstance(tp, UnionType):
            inner_types = get_args(tp)

        elif origin is Annotated:
            inner_types = get_args(tp)[:1]

        else:
            yield tp

            if with_origin and origin is not None:
                yield origin

            continue

        yield from standardize_types(*inner_types, with_origin=with_origin)
