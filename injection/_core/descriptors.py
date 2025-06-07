from typing import Self

from injection._core.common.invertible import Invertible
from injection._core.common.type import InputType
from injection._core.module import Module, mod


class LazyInstance[T]:
    __slots__ = ("__value",)

    __value: Invertible[T]

    def __init__(
        self,
        cls: InputType[T],
        /,
        default: T = NotImplemented,
        *,
        module: Module | None = None,
        threadsafe: bool | None = None,
    ) -> None:
        module = module or mod()
        self.__value = module.get_lazy_instance(cls, default, threadsafe=threadsafe)

    def __get__(
        self,
        instance: object | None = None,
        owner: type | None = None,
    ) -> Self | T:
        if instance is None:
            return self

        return ~self.__value
