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
from injection import mod
from injection.integrations.blacksheep import InjectionServices

custom_module = mod("custom_module")

app = Application(
    services=InjectionServices(custom_module),
)
```

## [FastAPI](https://github.com/fastapi/fastapi)

Exemple:

```python
from fastapi import FastAPI
from injection.integrations.fastapi import Inject

app = FastAPI()

@app.get("/")
async def my_endpoint(service: MyService = Inject(MyService)):
    ...
```
