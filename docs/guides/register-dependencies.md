# Register dependencies

`python-injection` provides four main decorators to register your dependencies: `@injectable`, `@singleton`, `@scoped`, and `@constant`. These decorators can be applied to classes, sync functions, or async functions. The `@scoped` decorator additionally supports sync and async generator functions for context manager support. For pre-existing values, use the `set_constant` function.

All constructor parameters and factory function parameters are automatically resolved based on their type annotations.

## Transient

A new instance is created every time the dependency is resolved.
```python
from injection import injectable


@injectable
class Dependency: ...
```

## Singleton

A single instance is created and shared across the entire application.
```python
from injection import singleton


@singleton
class Dependency: ...
```

!!! warning "Registration is locked once a singleton is created"
    As soon as a singleton instance is created, its module is **locked**: registering a new dependency or [loading a profile](profiles.md) then raises a `ModuleLockError`, because the existing instance could have been built with other dependencies. Register everything and load your profile before resolving any singleton.

## Constant

Register a pre-existing value as a dependency.
```python
from dataclasses import dataclass
from injection import set_constant


@dataclass(frozen=True)
class Settings:
    api_key: str


settings = set_constant(Settings("<secret_api_key>"))
```

You can also use type aliases to register constants for primitive types:
```python
from injection import set_constant

type APIKey = str

api_key = set_constant("<secret_api_key>", APIKey, alias=True)
```

For lazy constants, use the `@constant` decorator. The value is created on first resolution, then always reused. Unlike `@singleton`, its parameters are not resolved: the class or function must be callable without arguments.
```python
from injection import constant


@constant
class LazySettings: ...
```

## Factories

All decorators work with both sync and async functions.

_Make sure not to forget the return type annotation._
```python
from injection import injectable


class Dependency: ...


@injectable
def _dependency_factory() -> Dependency:
    # ...
    return Dependency()
```

!!! note
    A dependency created by an async function can only be resolved from an async context (see [Resolve dependencies](resolve-dependencies.md#inject)).

## Abstract classes

Register an implementation for an abstract class or protocol.

!!! warning
    Make sure the implementation is properly imported in your project for it to be registered (see [auto-imports](imports.md) section).
```python
from injection import injectable
from abc import ABC


class AbstractDependency(ABC): ...


@injectable(on=AbstractDependency)
class Dependency(AbstractDependency): ...
```

The dependency is registered both on its own class and on the types passed to `on`. To register it only on the types passed to `on`, set `ignore_type_hint=True`.

## Scoped

A single instance is created per scope (see [Scopes](scopes.md) to define one).
```python
from injection import scoped


@scoped("<scope_name>")
class Dependency: ...
```

Several scope names can be passed: the instance is then stored in the first of these scopes that is defined.
```python
@scoped("<scope_name>", "<other_scope_name>")
class Dependency: ...
```

## Scoped with context manager

Scoped dependencies can be registered using generator functions (sync or async) to handle setup and teardown logic. The teardown runs when the scope closes.

!!! note
    If you're unfamiliar with context managers, [see Python's context manager documentation](https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager).
```python
from collections.abc import Iterator
from injection import scoped


class Dependency:
    def open(self): ...

    def close(self): ...


@scoped("<scope_name>")
def dependency_factory() -> Iterator[Dependency]:
    dependency = Dependency()
    dependency.open()
    try:
        yield dependency
    finally:
        dependency.close()
```

## Advanced options

### Required registrations

`@should_be_injectable` declares a class that must be registered by another part of the code. Resolving it without an implementation raises an `InjectionError` explaining that the class should be an injectable, instead of a less explicit `NoInjectable`.
```python
from injection import should_be_injectable


@should_be_injectable
class Dependency: ...
```

### Disabling parameter resolution

By default, the parameters of a class or factory are resolved from their type annotations. Set `inject=False` to call it without arguments instead:
```python
from injection import injectable


@injectable(inject=False)
class Dependency:
    def __init__(self, value: int = 0): ...
```

## Profiles

Every decorator also exists on modules, to register a dependency for a specific profile only. See [Profiles](profiles.md).
