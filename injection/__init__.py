from .core import Injectable, Module
from .core import Mode as InjectableMode
from .core import Priority as ModulePriority

__all__ = (
    "Injectable",
    "InjectableMode",
    "Module",
    "ModulePriority",
    "get_instance",
    "get_lazy_instance",
    "inject",
    "injectable",
    "mod",
    "set_constant",
    "should_be_injectable",
    "singleton",
)


def mod(name: str = None, /) -> Module:
    if name is None:
        return Module.default()

    return Module.from_name(name)


get_instance = mod().get_instance
get_lazy_instance = mod().get_lazy_instance
inject = mod().inject
injectable = mod().injectable
resolve_instance = mod().resolve_instance
set_constant = mod().set_constant
should_be_injectable = mod().should_be_injectable
singleton = mod().singleton
