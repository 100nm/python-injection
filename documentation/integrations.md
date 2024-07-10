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

custom_module = Module.from_name("custom_module")

app = Application(
    services=InjectionServices(custom_module),
)
```
