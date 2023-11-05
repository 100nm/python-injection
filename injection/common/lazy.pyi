from typing import Iterable, Mapping, TypeVar

_K = TypeVar("_K")
_V = TypeVar("_V")

# noinspection PyAbstractClass
class LazyMapping(Mapping[_K, _V]):
    def __init__(self, iterable: Iterable[tuple[_K, _V]]): ...
