# Profiles

Profiles allow you to swap different implementations of dependencies based on your environment or context (e.g., development, production, staging). This is particularly useful when you need different database connections, API clients, or configurations depending on where your application runs.

## Modules

The `Module` object is the core component for managing dependencies within a profile. Each module represents a set of dependencies specific to a particular profile. You can retrieve a module instance using the `mod` function.

Storing your profile names in a `StrEnum` is recommended for type safety and consistency.
```python
from enum import StrEnum
from injection import mod

class Profile(StrEnum):
    DEV = "development"
    PROD = "production"
    STAGING = "staging"

# Get a module for a specific profile
dev_module = mod(Profile.DEV)
```

Once you have a module, you can use it to register dependencies that should only be available when that profile is active. The module provides access to all the registration decorators we've seen earlier (`injectable`, `singleton`, `scoped`, `constant`) as well as the `set_constant` method.

## Loading a profile

!!! warning "Caution"
    Always load your profile as early as possible in your program's execution, ideally at startup before any dependency resolution occurs.

### load_profile

For straightforward use cases, use the `load_profile` function:
```python
from injection.loaders import load_profile

load_profile(Profile.DEV)
```

This is the simplest approach when each profile is independent and doesn't share dependencies with other profiles.

### ProfileLoader

For more complex scenarios where profiles share common subsets of dependencies, use `ProfileLoader`:
```python
from injection.loaders import ProfileLoader

profile_loader = ProfileLoader({
    Profile.DEV: [SubProfile.STUB],
    Profile.TEST: [SubProfile.STUB],
})

profile_loader.load(Profile.DEV)
```

In this example, both "dev" and "test" profiles load the "stub" module, allowing you to reuse common mock implementations or shared configurations across multiple profiles.

!!! danger
    Only create a single `ProfileLoader` instance for your entire application to avoid conflicts. It's recommended to instantiate it at the Python module level (as a global variable) to ensure uniqueness.

#### Inspecting required modules

`ProfileLoader` provides a `required_module_names` method that returns the set of module names required by a profile. This is useful for debugging or validating your profile configuration.
```python
dev_modules = profile_loader.required_module_names(Profile.DEV)
# Returns: frozenset({<Profile.DEV: 'development'>, <SubProfile.STUB: 'stub'>, '__default__'})
```

### Using loaders as context managers

Both `load_profile` and `ProfileLoader` can be used as context managers. When the context exits, the profile is unloaded and all cached instances are cleared:
```python
with load_profile(Profile.DEV):
    # Dev profile is active
    run_app()

# Profile is unloaded, cache is cleared
```

With `ProfileLoader`:
```python
with profile_loader.load(Profile.DEV):
    # Dev profile is active
    run_app()

# Profile is unloaded, cache is cleared
```

This is particularly useful in testing scenarios where you want to ensure complete isolation between test runs.
