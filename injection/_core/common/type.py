from collections.abc import Callable, Iterable, Iterator
from inspect import get_annotations, isfunction
from types import UnionType
from typing import (
    Annotated,
    Any,
    NamedTuple,
    Self,
    Union,
    get_args,
    get_origin,
)

__all__ = ("TypeInfo", "TypeReport", "analyze_types", "get_return_types")

type TypeInfo[T] = type[T] | Callable[..., T] | Iterable[TypeInfo[T]] | UnionType


class TypeReport[T](NamedTuple):
    origin: type[T]
    args: tuple[Any, ...]

    @property
    def type(self) -> type[T]:
        origin = self.origin

        if args := self.args:
            return origin[*args]

        return origin

    @property
    def no_args(self) -> Self:
        if self.args:
            return type(self)(self.origin, ())

        return self


def analyze_types(*types: type | Any) -> Iterator[TypeReport[Any]]:
    for tp in types:
        if tp is None:
            continue

        origin = get_origin(tp)

        if origin is Union or isinstance(tp, UnionType):
            inner_types = get_args(tp)

        elif origin is Annotated:
            inner_types = get_args(tp)[:1]

        else:
            yield TypeReport(origin or tp, get_args(tp))
            continue

        yield from analyze_types(*inner_types)


def get_return_types(*args: TypeInfo[Any]) -> Iterator[type | UnionType]:
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
