# Custom scopes

Scopes allow you to control the lifetime of dependencies within a specific context. We've seen how to register scoped dependencies earlier. Now let's look at how to define and use scopes.

## Defining scopes

The `define_scope` context manager creates a scope for the duration of the context. It takes two parameters:

- **scope_name** (required): The name of the scope. Using a `StrEnum` to store scope names is recommended.
- **kind** (optional): Either `"contextual"` (default) or `"shared"`.

```python
from injection import define_scope

with define_scope("<scope_name>"):
    # Dependencies registered with this scope are available here
    ...
```

### Scope kinds

**Contextual scopes** (default) are based on [`ContextVar`](https://docs.python.org/3/library/contextvars.html#contextvars.ContextVar), meaning each concurrent context (like async tasks) maintains its own isolated scope:
```python
with define_scope("<scope_name>", kind="contextual"):
    # Each async task will have its own isolated scope
    ...
```

**Shared scopes** are based on global state, meaning all code within the scope shares the same dependency instances:
```python
with define_scope("<scope_name>", kind="shared"):
    # All code shares the same scope instances
    ...
```

### Async scopes

For dependencies instantiated with async context managers, the async version `adefine_scope` is required:
```python
from injection import adefine_scope

async with adefine_scope("<scope_name>"):
    # Async scoped dependencies are available here
    ...
```

## Defining scopes with bindings

`MappedScope` allows you to define scopes with associated data bindings. This is useful when you want to make specific values available within the scope context. **Bindings are injectable in all dependencies**, making them accessible throughout your dependency graph.
```python
from injection import MappedScope

type Locale = str

@dataclass
class Bindings:
    locale: Locale
    
    scope = MappedScope("<scope_name>")

with Bindings("fr_FR").scope.define():
    # Dependencies can now access the locale binding
    ...
```

The `define` method also accepts the `kind` parameter with the same `"contextual"` and `"shared"` options.

For async scopes with bindings, use `adefine`:
```python
async with Bindings("fr_FR").scope.adefine():
    ...
```

This pattern is particularly useful for request-scoped data in web applications, where each request might have its own set of contextual values that need to be accessible to dependencies within that request's scope.
