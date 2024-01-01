from typing import Any

__all__ = ("format_type", "get_origin")


def format_type(cls: type | Any) -> str:
    try:
        return f"{cls.__module__}.{cls.__qualname__}"
    except AttributeError:
        return str(cls)


def get_origin(cls: type | Any) -> type | Any:
    return getattr(cls, "__origin__", cls)
