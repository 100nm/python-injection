# Register dependencies

`python-injection` provides four main decorators to register your dependencies: `@injectable`, `@singleton`, `@scoped`, and `@constant`. These decorators can be applied to classes, sync functions, or async functions. The `@scoped` decorator additionally supports sync and async generator functions for context manager support. For pre-existing values, use the `set_constant` function.

All constructor parameters and factory function parameters are automatically resolved based on their type annotations.

## Transient

A new instance is created every time the dependency is resolved.
```python
from injection import injectable

@injectable
class Dependency:
    ...
```

## Singleton

A single instance is created and shared across the entire application.
```python
from injection import singleton

@singleton
class Dependency:
    ...
```

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

For lazy constants, use the `@constant` decorator:
```python
from injection import constant

@constant
class LazySettings:
    ...
```

## Factories

All decorators work with both sync and async functions.

_Make sure not to forget the return type annotation._
```python
from injection import injectable

class Dependency:
    ...

@injectable
def dependency_factory() -> Dependency:
    # ...
    return Dependency()
```

## Abstract classes

Register an implementation for an abstract class or protocol.

!!! warning
    Make sure the implementation is properly imported in your project for it to be registered (see [auto-imports](imports.md) section).
```python
from injection import injectable
from abc import ABC

class AbstractDependency(ABC):
    ...

@injectable(on=AbstractDependency)
class Dependency(AbstractDependency):
    ...
```

## Scoped

A single instance is created per scope. Using a `StrEnum` for scope names is recommended.
```python
from injection import scoped

@scoped("<scope_name>")
class Dependency:
    ...
```

## Scoped with context manager

Scoped dependencies can be registered using generator functions (sync or async) to handle setup and teardown logic.

!!! note
    If you're unfamiliar with context managers, [see Python's context manager documentation](https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager).
```python
from collections.abc import Iterator
from injection import scoped

class Dependency:
    def open(self):
        ...

    def close(self):
        ...

@scoped("<scope_name>")
def dependency_factory() -> Iterator[Dependency]:
    dependency = Dependency()
    dependency.open()
    try:
        yield dependency
    finally:
        dependency.close()
```

## Profiles

Register a dependency for a specific profile. Using a `StrEnum` for profile names is recommended.
```python
from injection import mod

@mod("<profile_name>").injectable
class Dependency:
    ...
```