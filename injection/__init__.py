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

default_module = Module(f"{__name__}:default_module")

get_instance = default_module.get_instance
inject = default_module.inject
injectable = default_module.injectable
singleton = default_module.singleton
