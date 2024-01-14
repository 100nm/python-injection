from .core import Module, ModulePriorities

__all__ = (
    "Module",
    "ModulePriorities",
    "constant",
    "default_module",
    "get_instance",
    "get_lazy_instance",
    "inject",
    "injectable",
    "singleton",
)

default_module = Module(f"{__name__}:default_module")

constant = default_module.constant
get_instance = default_module.get_instance
get_lazy_instance = default_module.get_lazy_instance

inject = default_module.inject
injectable = default_module.injectable
singleton = default_module.singleton
