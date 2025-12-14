# Thread safety

By default, `python-injection` is optimized for single-threaded performance. However, three components are not thread-safe: modules, dependency resolution, and scope definition.

## Modules

Module registration (using decorators like `@injectable`, `@singleton`, etc.) is not thread-safe. However, this is rarely an issue because modules are typically registered either:

- At the Python module level (executed once during import)
- In the main function before any concurrent execution

As long as you complete all module registration before spawning threads, you won't encounter issues.

## Dependency resolution and scope definition

Dependency resolution and scope definition are not thread-safe by default. If you need to resolve dependencies or define scopes in a multi-threaded environment, use the `threadsafe` parameter:
```python
from injection import define_scope, get_instance, inject

# Thread-safe dependency injection
@inject(threadsafe=True)
def function(dependency: Dependency):
    ...

# Thread-safe manual resolution
dependency = get_instance(Dependency, threadsafe=True)

# Thread-safe scope definition
with define_scope("<scope_name>", threadsafe=True):
    ...
```

The `threadsafe` parameter is available on all functions that resolve dependencies or define scopes.

## Global thread safety

If you need thread safety throughout your application, set the `PYTHON_INJECTION_THREADSAFE` environment variable:
```bash
export PYTHON_INJECTION_THREADSAFE=1
```

Or in Python:
```python
import os

os.environ["PYTHON_INJECTION_THREADSAFE"] = "1"
```

When this environment variable is set, all dependency resolution and scope operations become thread-safe by default.

!!! warning "Environment variable timing"
    The `PYTHON_INJECTION_THREADSAFE` environment variable is resolved at the Python module level when `injection` is first imported. If you set environment variables dynamically in your main function, they may not take effect. Set the environment variable before importing `injection` or before running your application.
```python
# ❌ Too late - injection already imported
import injection
os.environ["PYTHON_INJECTION_THREADSAFE"] = "1"

# ✅ Correct - set before import
os.environ["PYTHON_INJECTION_THREADSAFE"] = "1"
import injection
```

## Performance considerations

Thread safety comes with a performance cost due to locking mechanisms. Only enable it when actually needed:

- **Single-threaded applications**: Don't enable thread safety (default behavior is faster)
- **Multi-threaded applications**: Enable thread safety with the parameter or environment variable
