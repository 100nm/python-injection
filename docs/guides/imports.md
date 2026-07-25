# Auto-imports

When using decorators to register dependencies, some implementations may never be explicitly imported in your project. This creates a problem: if a module is never imported, its decorators never execute, and the dependencies are never registered.

For example, if you register an implementation with `@injectable(on=AbstractDependency)` but never import that implementation module, the dependency won't be available for injection even though it's decorated.

To solve this, `python-injection` provides two solutions for automatically importing modules in a package.

!!! tip
    Call auto-import functions early in your application startup, **before loading your profile** and before any dependency resolution occurs.

## load_packages

The `load_packages` function imports all modules from the specified packages. Packages can be passed as module objects or as strings:
```python
from injection.loaders import load_packages
from src import adapters, services

# Import all modules in adapters and services packages
load_packages(adapters, services)

# Or using string notation
load_packages("src.adapters", "src.services")
```

This is the simplest approach and works well when you want to import everything from specific packages.

## PythonModuleLoader

For more control over which modules get imported, use `PythonModuleLoader` with a custom predicate function. Like `load_packages`, it accepts both module objects and strings:
```python
from injection.loaders import PythonModuleLoader
from src import adapters, services


def predicate(module_name: str) -> bool:
    # Only import modules containing "impl" in their name
    return "impl" in module_name


PythonModuleLoader(predicate).load(adapters, services)
```

The predicate function receives the full module name (e.g., `"src.adapters.dependency_impl"`) and returns `True` if the module should be imported.

### Factory methods

`PythonModuleLoader` provides three convenient factory methods for common filtering patterns:

**Filter by prefix:**
```python
# Import only modules starting with "impl_"
PythonModuleLoader.startswith("impl_").load(adapters, services)
```

**Filter by suffix:**
```python
# Import only modules ending with "_impl"
PythonModuleLoader.endswith("_impl").load(adapters, services)
```

**Filter by keyword marker:**
```python
# Import only modules containing a specific comment
PythonModuleLoader.from_keywords("# auto-import").load(adapters, services)
```

This last approach is particularly useful for explicitly marking which modules should be auto-imported:
```python
# auto-import


@injectable(on=AbstractDependency)
class Dependency(AbstractDependency): ...
```
