# Entrypoint

## What is it?

_The entrypoint refers to the first function executed by the software._

Using `python-injection`, you may need to do several things at each entrypoint _(inject dependencies, open a scope or
even import Python modules)_.

To solve this problem, the package contains an `Entrypoint` class, a builder that simplifies the preparation of an
entrypoint.

## Create an entrypoint decorator

`Entrypoint.make_decorator` is a decorator for creating a decorator for an entrypoint function.

The decorate function is the method used to set up the `Entrypoint` object. The first parameter of the function is the
`Entrypoint` instance that will be built when the entrypoint function is decorated. It's possible to inject dependencies
into the setup method, but beware: at this stage, not everything can be configured, so make sure you only use
`injectables` or `constants`.

**The order of instructions matters**: internally, each builder instruction applies a decorator to the entrypoint
function and recreates an `Entrypoint` instance.

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
> If you want to create a decorator for async entrypoints, it's important to annotate `self` with `AsyncEntrypoint`,
> otherwise just use `Entrypoint`.

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