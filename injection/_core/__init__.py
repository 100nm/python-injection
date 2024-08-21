from collections.abc import Iterable
from typing import Any

from injection._core.common.type import InputType, standardize_types
from injection._core.hook import HookGenerator
from injection._core.module import Locator, Mode, Record, Updater

__all__ = ()


@Locator.static_hooks.on_conflict
def check_mode[T](
    new: Record[T],
    existing: Record[T],
    cls: InputType[T],
    *_: Any,
    **__: Any,
) -> HookGenerator[bool]:
    new_mode = new.mode
    is_override = new_mode == Mode.OVERRIDE

    if new_mode == existing.mode and not is_override:
        raise RuntimeError(f"An injectable already exists for the class `{cls}`.")

    value = yield
    return value or is_override


@Locator.static_hooks.on_conflict
def compare_mode_rank[T](
    new: Record[T],
    existing: Record[T],
    *_: Any,
    **__: Any,
) -> HookGenerator[bool]:
    value = yield
    return value or new.mode.rank > existing.mode.rank


@Locator.static_hooks.on_input
def standardize_input_classes[T](
    *_: Any,
    **__: Any,
) -> HookGenerator[Iterable[InputType[T]]]:
    classes = yield
    return tuple(standardize_types(*classes, with_origin=True))


@Locator.static_hooks.on_update
def standardize_classes[T](*_: Any, **__: Any) -> HookGenerator[Updater[T]]:
    updater = yield
    updater.classes = set(standardize_types(*updater.classes))
    return updater
