# Entrypoint

## What is it?

_An entrypoint is the first function executed when a software component starts._

When using `python-injection`, you often need to perform several setup actions at the entrypoint _(such as injecting
dependencies, opening a scope, or importing Python modules)_.

To solve this problem, the package provides an `Entrypoint` class, a builder-style utility that simplifies
entrypoint preparation.

## Creating an entrypoint decorator

`Entrypoint.make_decorator` allows you to define a custom decorator for your entrypoint functions.

The function you decorate with `make_decorator` serves to configure the `Entrypoint` instance. Its first parameter must
be the `Entrypoint` instance being built. You can inject dependencies into this setup function, but **only** `constants`
or `injectables`, because everything is not yet fully configured at this stage.

**Instruction order matters**: each configuration step applies a decorator and returns a new `Entrypoint` instance.

```python
# src/entrypoint.py

import uvloop
from injection import adefine_scope
from injection.entrypoint import AsyncEntrypoint, Entrypoint
from injection.loaders import PythonModuleLoader

@Entrypoint.make_decorator
def entrypoint[**P, T](self: AsyncEntrypoint[P, T]) -> Entrypoint[P, T]:
    import src
    
    loader = PythonModuleLoader.from_keywords("# Auto-import")
    return (
        self.inject()
        .decorate(adefine_scope("lifespan", kind="shared"))
        .async_to_sync(uvloop.run)
        .load_modules(loader, src)
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

from typer import Typer

from src.entrypoint import entrypoint
from src.services.logger import AsyncLogger  # project service, implementation not provided

app = Typer()

@app.command()
def hello(name: str) -> None:
    @entrypoint
    async def main(logger: AsyncLogger) -> None:
        await logger.info(f"Hello {name}!")

    main()
    
@app.command()
def goodbye(name: str) -> None:
    @entrypoint
    async def main(logger: AsyncLogger) -> None:
        await logger.info(f"Goodbye {name}!")
        
    main()

if __name__ == "__main__":
    app()
```