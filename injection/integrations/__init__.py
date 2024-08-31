from importlib.util import find_spec
from typing import Literal

__all__ = ("_is_installed",)


def _is_installed(package: str, needed_for: object, /) -> Literal[True]:
    if find_spec(package) is None:
        raise RuntimeError(f"To use `{needed_for}`, {package} must be installed.")

    return True
