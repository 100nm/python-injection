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
    "set_constant",
    "should_be_injectable",
    "singleton",
)

_module = Module.default()

get_instance = _module.get_instance
get_lazy_instance = _module.get_lazy_instance
inject = _module.inject
injectable = _module.injectable
set_constant = _module.set_constant
should_be_injectable = _module.should_be_injectable
singleton = _module.singleton

del _module
