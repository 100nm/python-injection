from typing import Any, Callable, Iterable, TypeVar, overload

_T = TypeVar("_T")

class Module:
    """
    Object with isolated injection environment.
    """

    def get_instance(self, reference: type[_T]) -> _T:
        """
        Function used to retrieve an instance associated with the type passed in parameter or raise `NoInjectable`
        exception.
        """
    def inject(self, wrapped: Callable[..., Any] = ..., /):
        """
        Decorator applicable to a class or function. Inject function dependencies using parameter type annotations. If
        applied to a class, the dependencies resolved will be those of the `__init__` method.

        Doesn't work with type annotations resolved by `__future__` module.
        """
    def injectable(self, *, reference: type = ..., auto_inject: bool = ...):
        """
        Decorator applicable to a class or function. It is used to indicate how the injectable will be constructed. At
        injection time, a new instance will be injected each time. Automatically injects constructor dependencies, can
        be disabled with `auto_inject=False`.
        """
    @overload
    def injectable(
        self,
        *,
        references: Iterable[type] = ...,
        auto_inject: bool = ...,
    ): ...
    def singleton(self, *, reference: type = ..., auto_inject: bool = ...):
        """
        Decorator applicable to a class or function. It is used to indicate how the singleton will be constructed. At
        injection time, the injected instance will always be the same. Automatically injects constructor dependencies,
        can be disabled with `auto_inject=False`.
        """
    @overload
    def singleton(
        self,
        *,
        references: Iterable[type] = ...,
        auto_inject: bool = ...,
    ): ...

def new_module() -> Module:
    """
    Function to create a new injection module.
    """
