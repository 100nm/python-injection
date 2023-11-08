from typing import Iterator, Mapping, TypeVar

_K = TypeVar("_K")
_V = TypeVar("_V")

# noinspection PyAbstractClass
class LazyMapping(Mapping[_K, _V]):
    """
    A mapping built using a generator. The generator is consumed to build a `dict` from the moment it's needed.
    """

    def __init__(self, iterator: Iterator[tuple[_K, _V]]): ...
