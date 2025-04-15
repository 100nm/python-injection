from ._core.descriptors import LazyInstance
from ._core.injectables import Injectable
from ._core.module import Mode, Module, Priority, mod
from ._core.scope import ScopeFacade as Scope
from ._core.scope import ScopeKind, adefine_scope, define_scope
from ._core.slots import SlotKey

__all__ = (
    "Injectable",
    "LazyInstance",
    "Mode",
    "Module",
    "Priority",
    "Scope",
    "ScopeKind",
    "SlotKey",
    "adefine_scope",
    "afind_instance",
    "aget_instance",
    "aget_lazy_instance",
    "constant",
    "define_scope",
    "find_instance",
    "get_instance",
    "get_lazy_instance",
    "inject",
    "injectable",
    "mod",
    "reserve_scoped_slot",
    "scoped",
    "set_constant",
    "should_be_injectable",
    "singleton",
)

afind_instance = mod().afind_instance
aget_instance = mod().aget_instance
aget_lazy_instance = mod().aget_lazy_instance
constant = mod().constant
find_instance = mod().find_instance
get_instance = mod().get_instance
get_lazy_instance = mod().get_lazy_instance
inject = mod().inject
injectable = mod().injectable
reserve_scoped_slot = mod().reserve_scoped_slot
scoped = mod().scoped
set_constant = mod().set_constant
should_be_injectable = mod().should_be_injectable
singleton = mod().singleton
