from types import NoneType, UnionType
from typing import Any, Iterator, Union, get_args

__all__ = ("format_type", "get_origin", "get_origins")


def format_type(cls: type | Any) -> str:
    try:
        return f"{cls.__module__}.{cls.__qualname__}"
    except AttributeError:
        return str(cls)


def get_origin(cls: type | Any) -> type | Any:
    return getattr(cls, "__origin__", cls)


def get_origins(*classes: type | UnionType | Any) -> Iterator[type | Any]:
    for cls in classes:
        if cls in (None, NoneType):
            continue

        origin = get_origin(cls)

        if origin is not Union:
            yield origin
            continue

        for argument in get_args(cls):
            yield from get_origins(argument)
