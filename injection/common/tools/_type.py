from types import NoneType, UnionType
from typing import Any, Iterator, Union, get_args

__all__ = ("format_type", "get_origins")


def format_type(cls: type | Any) -> str:
    try:
        return f"{cls.__module__}.{cls.__qualname__}"
    except AttributeError:
        return str(cls)


def get_full_origin(cls: type | Any) -> type | Any:
    try:
        origin = cls.__origin__
    except AttributeError:
        return cls

    return get_full_origin(origin)


def get_origins(*classes: type | Any) -> Iterator[type | Any]:
    for cls in classes:
        if cls in (None, NoneType):
            continue

        origin = get_full_origin(cls)

        if origin is Union or isinstance(cls, UnionType):
            for argument in get_args(cls):
                yield from get_origins(argument)

        else:
            yield origin
