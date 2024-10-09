import itertools
from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass, field
from inspect import isclass, isgeneratorfunction
from typing import Any, Self

from injection.exceptions import HookError

type HookGenerator[T] = Generator[None, T, T]
type HookFunction[**P, T] = Callable[P, T | HookGenerator[T]]


@dataclass(eq=False, frozen=True, slots=True)
class Hook[**P, T]:
    __functions: list[HookFunction[P, T]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def __call__(  # type: ignore[no-untyped-def]
        self,
        wrapped: HookFunction[P, T] | type[HookFunction[P, T]] | None = None,
        /,
    ):
        def decorator(wp):  # type: ignore[no-untyped-def]
            self.add(wp() if isclass(wp) else wp)
            return wp

        return decorator(wrapped) if wrapped else decorator

    @property
    def __stack(self) -> Iterator[HookFunction[P, T]]:
        return iter(self.__functions)

    def add(self, *functions: HookFunction[P, T]) -> Self:
        self.__functions.extend(reversed(functions))
        return self

    @classmethod
    def apply_several(cls, handler: Callable[P, T], *hooks: Self) -> Callable[P, T]:
        stack = itertools.chain.from_iterable((hook.__stack for hook in hooks))
        return cls.__apply_stack(handler, stack)

    @classmethod
    def __apply_function(
        cls,
        handler: Callable[P, T],
        function: HookFunction[P, T],
    ) -> Callable[P, T]:
        if not cls.__is_generator_function(function):
            return function  # type: ignore[return-value]

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            hook: HookGenerator[T] = function(*args, **kwargs)  # type: ignore[assignment]

            try:
                next(hook)

                try:
                    value = handler(*args, **kwargs)
                except BaseException as exc:
                    hook.throw(exc)
                else:
                    hook.send(value)
                    return value

            except StopIteration as stop:
                return stop.value

            finally:
                hook.close()

            raise HookError("Missing return value.")

        return wrapper

    @classmethod
    def __apply_stack(
        cls,
        handler: Callable[P, T],
        stack: Iterator[HookFunction[P, T]],
    ) -> Callable[P, T]:
        for function in stack:
            new_handler = cls.__apply_function(handler, function)
            return cls.__apply_stack(new_handler, stack)

        return handler

    @staticmethod
    def __is_generator_function(obj: Any) -> bool:
        for o in obj, getattr(obj, "__call__", None):
            if isgeneratorfunction(o):
                return True

        return False


def apply_hooks[**P, T](
    handler: Callable[P, T],
    hook: Hook[P, T],
    *hooks: Hook[P, T],
) -> Callable[P, T]:
    return Hook.apply_several(handler, hook, *hooks)
