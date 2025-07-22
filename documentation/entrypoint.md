# Entrypoint

## What is it?

_An entrypoint is the first function executed when software starts._

When using `python-injection`, you often need to perform several setup actions at the entrypoint _(such as injecting
dependencies, opening a scope, or importing Python modules)_.

To solve this problem, the package provides an `Entrypoint` class, a builder-style utility that simplifies
entrypoint preparation.

## Creating an entrypoint decorator

`entrypointmaker` allows you to define a custom decorator for your entrypoint functions.

The function you decorate with `entrypointmaker` serves to configure the `Entrypoint` instance. Its first parameter must
be the `Entrypoint` instance being built. You can inject dependencies into this setup function, but **only** `constants`
or `injectables`, because everything is not yet fully configured at this stage.

**Instruction order matters**: each configuration step applies a decorator and returns a new `Entrypoint` instance.

Here's all you can do with an entrypoint _(take only what you need)_:

```python
# src/entrypoint.py

from enum import StrEnum, auto

import uvloop
from injection import adefine_scope, mod
from injection.entrypoint import AsyncEntrypoint, Entrypoint, entrypointmaker
from injection.loaders import ProfileLoader, PythonModuleLoader
from pydantic_settings import BaseSettings

class Profile(StrEnum):
    DEFAULT = mod().name
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"
    
class SubProfile(StrEnum):
    CONF = "conf"
    
class Scope(StrEnum):
    LIFESPAN = auto()

@mod(SubProfile.CONF).constant
class Conf(BaseSettings):
    profile: Profile = Profile.DEFAULT
    
@entrypointmaker(profile_loader=ProfileLoader({Profile.DEFAULT: [SubProfile.CONF]}))
def entrypoint[**P, T](self: AsyncEntrypoint[P, T], conf: Conf) -> Entrypoint[P, T]:
    import src

    profile = conf.profile
    keyword = "# auto-import"
    keywords = {
        f"{keyword}: {name}"
        for name in self.profile_loader.required_module_names(profile)
    }
    module_loader = PythonModuleLoader.from_keywords(keyword, *keywords)
    return (
        self.inject()
        .decorate(adefine_scope(Scope.LIFESPAN, kind="shared"))
        .async_to_sync(uvloop.run)
        .load_modules(module_loader, src)
        .load_profile(profile)
    )
```

> [!IMPORTANT]
> **Typing rule**
> 
> When creating a decorator for async entrypoints, make sure to type `self` as `AsyncEntrypoint`. 
> For sync code, use `Entrypoint` instead.

## Example of use

Developing a CLI is a good example of using multiple entrypoints:

```python
# src/cli.py

from injection.entrypoint import autocall
from typer import Typer

from src.entrypoint import entrypoint  # the previously defined `entrypoint` decorator
from src.services.logger import AsyncLogger  # project service, implementation not provided

app = Typer()

@app.command()
def hello(name: str) -> None:
    @autocall   # allows automatically calling the function
    @entrypoint
    async def _(logger: AsyncLogger) -> None:
        await logger.info(f"Hello {name}!")
    
@app.command()
def goodbye(name: str) -> None:
    @autocall
    @entrypoint
    async def _(logger: AsyncLogger) -> None:
        await logger.info(f"Goodbye {name}!")

if __name__ == "__main__":
    app()
```