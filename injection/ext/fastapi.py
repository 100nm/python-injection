from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from types import GenericAlias
from typing import Annotated, Any, TypeAlias, TypeAliasType

from fastapi import Depends

from injection import Module, mod

__all__ = ("Inject", "InjectThreadSafe")


@dataclass(eq=False, frozen=True, slots=True)
class FastAPIInject:
    module: Module = field(default_factory=mod)
    threadsafe: bool | None = field(default=None, kw_only=True)

    def __call__[T](
        self,
        cls: type[T] | TypeAliasType | GenericAlias,
        /,
        default: T = NotImplemented,
        *,
        module: Module | None = None,
        threadsafe: bool | None = None,
    ) -> Any:
        module = module or self.module
        threadsafe = self.threadsafe if threadsafe is None else threadsafe
        awaitable = module.aget_lazy_instance(cls, default, threadsafe=threadsafe)
        dependency = self.__make_dependency(awaitable)
        dependency.__name__ = f"Inject[{getattr(cls, '__name__', str(cls))}]"
        return Depends(dependency, use_cache=False)

    def __getitem__[T, *Ts](self, params: T | tuple[T, *Ts], /) -> TypeAlias:
        iter_params = iter(params if isinstance(params, tuple) else (params,))
        cls = next(iter_params)
        return Annotated[cls, self(cls), *iter_params]

    @staticmethod
    def __make_dependency[T](awaitable: Awaitable[T]) -> Callable[[], Awaitable[T]]:
        async def dependency() -> T:
            return await awaitable

        return dependency


Inject = FastAPIInject()
InjectThreadSafe = FastAPIInject(threadsafe=True)

del FastAPIInject
