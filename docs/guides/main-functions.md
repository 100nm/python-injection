# Set up main functions

A main function often needs some setup before running: importing modules, loading a profile, defining scopes, injecting dependencies. This becomes repetitive when your project has several entry points (CLI commands, workers, scripts, etc.).

To solve this, `python-injection` provides **entrypoints**: custom decorators that apply all your setup logic, built step by step.

## Creating an entrypoint

Use the `@entrypointmaker` decorator to define your setup logic once. The simplest entrypoint only injects dependencies:
```python
from injection.entrypoint import Entrypoint, entrypointmaker


@entrypointmaker
def entrypoint[**P, T](self: Entrypoint[P, T]) -> Entrypoint[P, T]:
    return self.inject()
```

Then use your custom `@entrypoint` decorator on any function:
```python
@entrypoint
def main(dependency: Dependency = NotImplemented): ...


if __name__ == "__main__":
    main()
```

The builder provides the following steps:

- **`inject()`**: injects the dependencies of the main function.
- **`load_modules(loader, *packages)`**: imports modules with a [`PythonModuleLoader`](imports.md#pythonmoduleloader). Packages can be passed as strings.
- **`load_profile(name)`**: loads a [profile](profiles.md) (see [below](#integrating-with-profileloader)).
- **`decorate(decorator)`**: applies any decorator, such as a scope definition.
- **`async_to_sync(run=asyncio.run)`**: turns an async main function into a sync one.

A complete setup for an async main function looks like this:
```python
from injection import adefine_scope
from injection.entrypoint import AsyncEntrypoint, Entrypoint, entrypointmaker
from injection.loaders import PythonModuleLoader


@entrypointmaker
def entrypoint[**P, T](self: AsyncEntrypoint[P, T]) -> Entrypoint[P, T]:
    module_loader = PythonModuleLoader.endswith("_impl")
    return (
        self.inject()
        .decorate(adefine_scope("lifespan", kind="shared"))
        .async_to_sync()
        .load_modules(module_loader, "src")
    )


@entrypoint
async def main(dependency: Dependency = NotImplemented): ...


if __name__ == "__main__":
    main()
```

!!! info "Builder execution order"
    The builder steps execute in **reverse order**. Each step wraps the main function again, so the last step of the chain is called first. In the example above, modules are loaded first, then the function is converted to sync, then the scope is defined, and finally dependencies are injected.

### Automatic execution

The entrypoint decorator accepts an optional `autocall` parameter. When set to `True`, the decorated function is called as soon as it is decorated:
```python
@entrypoint(autocall=True)
async def main(dependency: Dependency = NotImplemented):
    # This function runs automatically when the module is executed
    ...
```

This is particularly convenient for scripts and CLI commands where you want the entry point to execute immediately.

## Integrating with ProfileLoader

If you're using a [`ProfileLoader`](profiles.md#profileloader) in your project, pass it to `@entrypointmaker` using the `profile_loader` parameter, then load a profile with `load_profile`:
```python
from injection.entrypoint import Entrypoint, entrypointmaker
from injection.loaders import ProfileLoader, PythonModuleLoader

profile_loader = ProfileLoader(...)


@entrypointmaker(profile_loader=profile_loader)
def entrypoint[**P, T](self: Entrypoint[P, T]) -> Entrypoint[P, T]:
    module_loader = PythonModuleLoader.endswith("_impl")
    return (
        self.inject()
        # Profile is the StrEnum defined in the Profiles guide
        .load_profile(Profile.DEV)
        .load_modules(module_loader, "src")
    )
```

The profile is loaded before the main function executes, and unloaded once it returns.

## Resolving dependencies in the setup

You can resolve dependencies from the setup function parameters. This is particularly useful for resolving configuration to determine which profile to load:
```python
from dataclasses import dataclass
from injection import constant
from injection.entrypoint import Entrypoint, entrypointmaker
from injection.loaders import ProfileLoader, PythonModuleLoader
from os import getenv

profile_loader = ProfileLoader(...)


@dataclass
class Config:
    profile: Profile


@constant
def _config_factory() -> Config:
    profile = Profile(getenv("PROFILE", "development"))
    return Config(profile)


@entrypointmaker(profile_loader=profile_loader)
def entrypoint[**P, T](self: Entrypoint[P, T], config: Config) -> Entrypoint[P, T]:
    profile = config.profile
    suffixes = self.profile_loader.required_module_names(profile)
    module_loader = PythonModuleLoader.endswith(*suffixes)
    return self.inject().load_profile(profile).load_modules(module_loader, "src")
```

In this example, `config` is resolved from the default module and used to load the matching profile.

The module loader relies on a naming convention: each module that registers dependencies for a profile ends with that profile's name. With the `development` profile, `src/mailer_development.py` is imported and `src/mailer_production.py` is not. Since `required_module_names` also returns the profile's [subsets](profiles.md#profileloader) and the default module (`__default__`), their modules are imported too.

!!! warning
    The setup function runs as soon as `@entrypointmaker` is applied, before any profile is loaded. Its dependencies must therefore be registered with the default decorators (not in a profile), and should be transient or constant: a singleton would lock the module and prevent the profile from loading (see [Singleton](register-dependencies.md#singleton)).
