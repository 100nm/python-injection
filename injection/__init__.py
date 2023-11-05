from .core import Module, new_module

__all__ = (
    "Module",
    "get_instance",
    "inject",
    "injectable",
    "new_module",
    "singleton",
)

_default_module = new_module()

get_instance = _default_module.get_instance
inject = _default_module.inject
injectable = _default_module.injectable
singleton = _default_module.singleton
