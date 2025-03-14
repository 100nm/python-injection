from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Generator,
    Iterable,
    Iterator,
)
from inspect import isfunction
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
type TypeInfo[T] = (
    InputType[T]
    | Callable[..., T]
    | Callable[..., Awaitable[T]]
    | Iterable[TypeInfo[T]]
)


def get_return_types(*args: TypeInfo[Any]) -> Iterator[InputType[Any]]:
    for arg in args:
        if isinstance(arg, Iterable) and not (
            isinstance(arg, type | str) or isinstance(get_origin(arg), type)
        ):
            inner_args = arg

        elif isfunction(arg) and (return_type := get_return_hint(arg)):
            inner_args = (return_type,)

        else:
            yield arg  # type: ignore[misc]
            continue

        yield from get_return_types(*inner_args)


def get_return_hint[T](function: Callable[..., T]) -> InputType[T] | None:
    return get_type_hints(function).get("return")


def get_yield_hint[T](
    function: Callable[..., Iterator[T]] | Callable[..., AsyncIterator[T]],
) -> InputType[T] | None:
    return_type = get_return_hint(function)

    if get_origin(return_type) not in {
        AsyncGenerator,
        AsyncIterable,
        AsyncIterator,
        Generator,
        Iterable,
        Iterator,
    }:
        return None

    args = get_args(return_type)
    return next(iter(args), None)


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
