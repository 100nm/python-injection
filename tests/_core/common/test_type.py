from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

import pytest

from injection._core.common.type import get_yield_types


class A: ...


def _iterator() -> Iterator[A]:
    raise NotImplementedError


async def _async_iterator() -> AsyncIterator[A]:
    raise NotImplementedError


def _function() -> A:
    raise NotImplementedError


@pytest.mark.parametrize(
    ("function", "expected"),
    [
        (_iterator, (A,)),
        (_async_iterator, (A,)),
        (_function, ()),
    ],
)
def test_get_yield_types_with_return_type_returns_yield_types(
    expected: tuple[Any, ...],
    function: Callable[..., Any],
) -> None:
    assert get_yield_types(function) == expected
