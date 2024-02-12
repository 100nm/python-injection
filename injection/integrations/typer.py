from typing import TypeVar

from typer import Option

_T = TypeVar("_T")


def skip():
    def get_none(*__args):
        return None

    return Option(
        default_factory=get_none,
        parser=get_none,
        hidden=True,
    )
