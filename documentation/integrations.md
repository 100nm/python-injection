# Integrations

**Integrations make it easy to connect `python-injection` to other frameworks.**

## [BlackSheep](https://github.com/Neoteroi/BlackSheep)

_[See more](https://www.neoteroi.dev/blacksheep/dependency-injection) about BlackSheep and its dependency injection._

Example:

```python
from blacksheep import Application
from injection.integrations.blacksheep import InjectionServices

app = Application(
    services=InjectionServices(),
)
```

Example with a custom injection module:

```python
from blacksheep import Application
from injection import Module
from injection.integrations.blacksheep import InjectionServices

custom_module = Module(f"{__name__}:custom_module")

app = Application(
    services=InjectionServices(custom_module),
)
```

## [Typer](https://github.com/tiangolo/typer)

Example:

```python
from injection.integrations.typer import injected
from typer import Typer

app = Typer()

@app.command()
def my_command(dependency: injected(Dependency)):
    """ command implementation """
```
