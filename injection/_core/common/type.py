from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Collection,
    Generator,
    Iterable,
    Iterator,
)
from inspect import isclass, isfunction
from types import GenericAlias, UnionType
from typing import (
    Any,
    TypeAliasType,
    get_args,
    get_origin,
    get_type_hints,
)

type InputType[T] = type[T] | TypeAliasType | GenericAlias | UnionType
type TypeInfo[T] = (
    InputType[T]
    | Callable[..., T]
    | Callable[..., Awaitable[T]]
    | Collection[TypeInfo[T]]
)


def get_return_hint[T](function: Callable[..., T]) -> InputType[T] | None:
    return get_type_hints(function).get("return")


def get_yield_hints[T](
    function: Callable[..., Iterator[T]] | Callable[..., AsyncIterator[T]],
) -> tuple[InputType[T]] | tuple[()]:
    return_type = get_return_hint(function)

    if get_origin(return_type) in (
        AsyncGenerator,
        AsyncIterable,
        AsyncIterator,
        Generator,
        Iterable,
        Iterator,
    ):
        for arg in get_args(return_type):
            return (arg,)

    return ()


def iter_return_types(*args: TypeInfo[Any]) -> Iterator[InputType[Any]]:
    for arg in args:
        if isinstance(arg, Collection) and not isclass(arg):
            inner_args = arg

        elif isfunction(arg) and (return_type := get_return_hint(arg)):
            inner_args = (return_type,)

        else:
            yield arg  # type: ignore[misc]
            continue

        yield from iter_return_types(*inner_args)
