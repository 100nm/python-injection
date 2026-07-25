# Set up main functions

As we've seen throughout this guide, there can be quite a bit of setup around a main function: loading modules, defining scopes, injecting dependencies, loading profiles, etc. This becomes repetitive when you have multiple entry points in your project (CLI commands, etc.).

To solve this, `python-injection` provides **entrypoints**, a way to create custom decorators that encapsulate all your setup logic using a builder pattern.

## Creating an entrypoint

Use the `@entrypointmaker` decorator to define your setup logic once:
```python
from injection import adefine_scope
from injection.entrypoint import AsyncEntrypoint, Entrypoint, entrypointmaker
from injection.loaders import PythonModuleLoader


@entrypointmaker
def entrypoint[**P, T](self: AsyncEntrypoint[P, T]) -> Entrypoint[P, T]:
    import src

    module_loader = PythonModuleLoader.endswith("_impl")
    return (
        self.inject()
        .decorate(adefine_scope("lifespan", kind="shared"))
        .async_to_sync()
        .load_modules(module_loader, src)
    )
```

Now you can use your custom `@entrypoint` decorator on any function:
```python
@entrypoint
async def main(dependency: Dependency):
    # All setup is automatically applied
    ...


if __name__ == "__main__":
    main()
```

!!! info "Builder execution order"
    The builder instructions execute in **reverse order**. Each method call re-decorates the main function, so the last instruction in the chain is call first. In the example above, modules are loaded first, then the function is converted to sync, then the scope is defined, and finally dependencies are injected.

### Automatic execution

The entrypoint decorator accepts an optional `autocall` parameter. When set to `True`, the decorated function is automatically called:
```python
@entrypoint(autocall=True)
async def main(dependency: Dependency):
    # This function runs automatically when the module is executed
    ...
```

This is particularly convenient for scripts and CLI commands where you want the entry point to execute immediately.

## Integrating with ProfileLoader

If you're using a [`ProfileLoader`](profiles.md#profileloader) in your project, pass it to `@entrypointmaker` using the `profile_loader` parameter:
```python
from injection.entrypoint import Entrypoint, entrypointmaker
from injection.loaders import ProfileLoader, PythonModuleLoader

profile_loader = ProfileLoader(...)


@entrypointmaker(profile_loader=profile_loader)
def entrypoint[**P, T](self: Entrypoint[P, T]) -> Entrypoint[P, T]:
    import src

    module_loader = PythonModuleLoader.endswith("_impl")
    return (
        self.inject()
        .load_profile(Profile.DEV)  # Load a specific profile
        .load_modules(module_loader, src)
    )
```

The `load_profile` method accepts a profile name and loads it before the main function executes.

## Resolving dependencies in the setup

You can resolve dependencies from the setup function parameters. These dependencies must be registered in the default module (not in a profile-specific module) and should preferably be transient or constant. This is particularly useful for resolving configuration to determine which profile to load:
```python
from dataclasses import dataclass
from injection import constant
from injection.entrypoint import Entrypoint, entrypointmaker
from injection.loaders import PythonModuleLoader
from os import getenv


@dataclass
class Config:
    profile: Profile


@constant
def _config_factory() -> Config:
    profile = Profile(getenv("PROFILE", "development"))
    return Config(profile)


@entrypointmaker(profile_loader=profile_loader)
def entrypoint[**P, T](self: Entrypoint[P, T], config: Config) -> Entrypoint[P, T]:
    import src

    profile = config.profile  # Use config to determine profile
    suffixes = self.profile_loader.required_module_names(profile)
    module_loader = PythonModuleLoader.endswith(*suffixes)
    return self.inject().load_profile(profile).load_modules(module_loader, src)
```

In this example, `config` is resolved from the default module and used to dynamically load the appropriate profile.

!!! warning
    Dependencies resolved in the entrypoint setup function must be registered in the default module (not in a profile-specific module) and should be transient or constant to avoid state issues.
