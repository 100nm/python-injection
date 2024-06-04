from .core import Injectable, Module
from .core import Mode as InjectableMode
from .core import Priority as ModulePriority

__all__ = (
    "Injectable",
    "InjectableMode",
    "Module",
    "ModulePriority",
    "default_module",
    "get_instance",
    "get_lazy_instance",
    "inject",
    "injectable",
    "set_constant",
    "should_be_injectable",
    "singleton",
)

default_module = Module(f"{__name__}:default_module")

get_instance = default_module.get_instance
get_lazy_instance = default_module.get_lazy_instance
inject = default_module.inject
injectable = default_module.injectable
set_constant = default_module.set_constant
should_be_injectable = default_module.should_be_injectable
singleton = default_module.singleton
