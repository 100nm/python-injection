from .core import Injectable, Module, ModulePriorities

__all__ = (
    "Injectable",
    "Module",
    "ModulePriorities",
    "default_module",
    "get_instance",
    "get_lazy_instance",
    "inject",
    "injectable",
    "set_constant",
    "singleton",
)

default_module = Module(f"{__name__}:default_module")

get_instance = default_module.get_instance
get_lazy_instance = default_module.get_lazy_instance
inject = default_module.inject
injectable = default_module.injectable
set_constant = default_module.set_constant
singleton = default_module.singleton
