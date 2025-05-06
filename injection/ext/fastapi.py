from types import GenericAlias
from typing import Annotated, Any, TypeAliasType

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
        ainstance = (module or mod()).aget_lazy_instance(cls, default)

        async def dependency() -> T:
            return await ainstance

        class_name = getattr(cls, "__name__", str(cls))
        dependency.__name__ = f"inject({class_name})"
        return Depends(dependency, use_cache=False)

    def __getitem__(self, params: Any, /) -> Any:
        iter_params = iter(params if isinstance(params, tuple) else (params,))
        cls = next(iter_params)
        return Annotated[cls, self(cls), *iter_params]


Inject = FastAPIInject()

del FastAPIInject
