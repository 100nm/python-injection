from .core import Module, ModulePriorities

__all__ = (
    "Module",
    "ModulePriorities",
    "default_module",
    "get_instance",
    "inject",
    "injectable",
    "singleton",
)

default_module = Module()

get_instance = default_module.get_instance
inject = default_module.inject
injectable = default_module.injectable
singleton = default_module.singleton
