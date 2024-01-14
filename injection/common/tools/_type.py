from collections.abc import Iterator
from types import NoneType, UnionType
from typing import Annotated, Any, Union, get_args, get_origin

__all__ = ("format_type", "get_origins")


def format_type(cls: type | Any) -> str:
    try:
        return f"{cls.__module__}.{cls.__qualname__}"
    except AttributeError:
        return str(cls)


def get_origins(*classes: type | Any) -> Iterator[type | Any]:
    for cls in classes:
        origin = get_origin(cls) or cls

        if origin in (None, NoneType):
            continue

        arguments = get_args(cls)

        if origin in (Union, UnionType):
            yield from get_origins(*arguments)

        elif origin is Annotated:
            try:
                annotated = arguments[0]
            except IndexError:
                continue

            yield from get_origins(annotated)

        else:
            yield origin
