from dataclasses import dataclass, field
from types import GenericAlias
from typing import Annotated, Any, TypeAliasType

from fastapi import Depends

from injection import Module, mod

__all__ = ("Inject", "InjectThreadSafe")


@dataclass(eq=False, frozen=True, slots=True)
class FastAPIInject:
    module: Module = field(default_factory=mod)
    threadsafe: bool = field(default=False, kw_only=True)

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
        ainstance = module.aget_lazy_instance(cls, default, threadsafe=threadsafe)

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
InjectThreadSafe = FastAPIInject(threadsafe=True)

del FastAPIInject
