from collections.abc import Iterable, Iterator
from inspect import get_annotations, isfunction
from types import NoneType, UnionType
from typing import Annotated, Any, Union, get_args, get_origin

__all__ = ("find_types", "format_type", "get_origins")


def format_type(cls: type | Any) -> str:
    try:
        return f"{cls.__module__}.{cls.__qualname__}"
    except AttributeError:
        return str(cls)


def get_origins(*types: type | Any) -> Iterator[type | Any]:
    for tp in types:
        origin = get_origin(tp) or tp

        if origin in (None, NoneType):
            continue

        elif origin in (Union, UnionType):
            args = get_args(tp)

        elif origin is Annotated is not tp:
            args = get_args(tp)[:1]

        else:
            yield origin
            continue

        yield from get_origins(*args)


def find_types(*args: Any) -> Iterator[type | UnionType]:
    for argument in args:
        if isinstance(argument, Iterable) and not isinstance(argument, type | str):
            arguments = argument

        elif isfunction(argument):
            arguments = (get_annotations(argument, eval_str=True).get("return"),)

        else:
            yield argument
            continue

        yield from find_types(*arguments)
