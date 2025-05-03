from types import GenericAlias
from typing import TYPE_CHECKING, Annotated, Any, TypeAliasType

from fastapi import Depends

from injection import Module, mod

__all__ = ("Inject",)


class FastAPIInject:
    __slots__ = ()

    def __call__[T](
        self,
        cls: type[T] | TypeAliasType | GenericAlias,
        /,
        default: T = NotImplemented,
        module: Module | None = None,
    ) -> Any:
        module = module or mod()
        lazy_instance = module.aget_lazy_instance(cls, default)

        async def getter() -> T:
            return await lazy_instance

        return Depends(getter, use_cache=False)

    def __getitem__(self, params: Any, /) -> Any:
        if not isinstance(params, tuple):
            params = (params,)

        iter_params = iter(params)
        cls = next(iter_params)
        return Annotated[cls, self(cls), *iter_params]


if TYPE_CHECKING:
    type Inject[T, *Args] = Annotated[T, Depends(), *Args]

else:
    Inject = FastAPIInject()

del FastAPIInject
