from collections.abc import Callable, Iterable, Iterator
from inspect import get_annotations, isfunction
from types import UnionType
from typing import (
    Annotated,
    Any,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
)

__all__ = (
    "InputType",
    "TypeDef",
    "TypeInfo",
    "analyze_types",
    "get_return_types",
)

type TypeDef[T] = type[T] | TypeAliasType

type InputType[T] = TypeDef[T] | UnionType

type TypeInfo[T] = InputType[T] | Callable[..., T] | Iterable[TypeInfo[T]]


def analyze_types(*types: InputType[Any], with_origin: bool = False) -> TypeDef[Any]:
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

        yield from analyze_types(*inner_types, with_origin=with_origin)


def get_return_types(*args: TypeInfo[Any]) -> Iterator[InputType[Any]]:
    for arg in args:
        if isinstance(arg, Iterable) and not (
            isinstance(arg, type | str) or isinstance(get_origin(arg), type)
        ):
            inner_args = arg

        elif isfunction(arg):
            inner_args = (get_annotations(arg, eval_str=True).get("return"),)

        else:
            yield arg
            continue

        yield from get_return_types(*inner_args)
