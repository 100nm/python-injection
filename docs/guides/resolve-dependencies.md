# Resolve dependencies

## Inject

The `@inject` decorator automatically resolves function parameters based on their type annotations when the function is called.
```python
from injection import inject

@inject
def function(dependency: Dependency):
    ...

function()  # You can now call `function` without arguments
```

When `@inject` is applied to an async function, it can resolve dependencies that require an async context. If an async dependency is required by a sync function decorated with `@inject`, a `RuntimeError` will be raised.

**Performance note:** The first call to an injected function is slower because it performs dependency resolution. Subsequent calls are faster as the resolution is cached.

### Static type checkers

Static type checkers like mypy will complain about missing arguments when calling injected functions:
```python
@inject
def function(dependency: Dependency):
    ...

function()  # <- mypy error: Missing positional argument "dependency" in call to "function"  [call-arg]
```

To fix this, provide a default value for injected parameters:
```python
@inject
def function(dependency: Dependency = NotImplemented):
    ...

function()  # <- OK
```

Using `NotImplemented` as the default value is recommended because it acts as a sentinel value: if the function is called without injection, any attempt to use the dependency will produce a clear and understandable error.

### asfunction

The `@asfunction` decorator provides an alternative to `@inject` for cases where frameworks don't allow unknown parameters in their functions.
```python
from injection import asfunction
from typing import NamedTuple

@asfunction
class Function(NamedTuple):
    dependency: Dependency

    def __call__(self, foo: str, bar: str, baz: str):
        # Use self.dependency here
        ...

# Call with only the runtime parameters
Function("foo", "bar", "baz")
```

**When to use `@asfunction`:**

In most cases, the `@inject` decorator is sufficient. However, some frameworks strictly validate function signatures and raise errors when they encounter unexpected parameters. The `@asfunction` decorator solves this by separating injected dependencies (defined as class attributes) from runtime parameters (defined in `__call__`).

Using `NamedTuple` is recommended for its concise syntax and built-in immutability.

## Getters

Getters provide an alternative way to retrieve dependencies without using the `@inject` decorator. They are particularly useful when you need to resolve dependencies programmatically or in contexts where decorators aren't suitable.

### find_instance

Returns the instance of the specified type or raises `NoInjectable` if not found.
```python
from injection import find_instance

dependency = find_instance(Dependency)
```

This is useful when you expect the dependency to always be available and want to fail fast if it's not registered.

### get_instance

Returns the instance of the specified type or `NotImplemented` if not found.
```python
from injection import get_instance

dependency = get_instance(Dependency)
```

### get_lazy_instance

Returns an object with the `__invert__` operator implemented. Calling `~` on this object resolves and returns the instance, or `NotImplemented` if not found.
```python
from injection import get_lazy_instance

lazy_dependency = get_lazy_instance(Dependency)
# ... later in your code
dependency = ~lazy_dependency
```

This is useful when you want to defer dependency resolution until it's actually needed.

### Async variants

All three getters have async versions prefixed with `a`:
```python
from injection import afind_instance, aget_instance, aget_lazy_instance

# Async variants
dependency = await afind_instance(Dependency)
dependency = await aget_instance(Dependency)

lazy_dependency = aget_lazy_instance(Dependency)
dependency = await lazy_dependency  # Note: awaitable instead of invertible
```

The async version of `get_lazy_instance` returns an awaitable instead of an invertible object.

## Descriptors

### LazyInstance

`LazyInstance` is a descriptor that acts as a getter, resolving the dependency each time it's accessed via `self`.
```python
from injection import LazyInstance

class Class:
    dependency = LazyInstance(Dependency)
    
    def do_something(self):
        self.dependency.some_method()  # Resolved on every access
```

**Important:** Dependencies requiring an async context are not compatible with `LazyInstance` since descriptors cannot be awaited.
