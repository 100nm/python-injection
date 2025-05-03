# Integrations

**Integrations make it easy to connect `python-injection` to other frameworks.**

## [FastAPI](https://github.com/fastapi/fastapi)

### Inject a dependency

Here's how to inject an instance into a FastAPI endpoint.

```python
from injection.ext.fastapi import Inject

@app.get("/")
async def my_endpoint(service: Inject[MyService]) -> None:
    ...
```

### Useful scopes

Two fairly common scopes in FastAPI:
* **Application lifespan scope**: associate with application lifespan.
* **Request scope**: associate with http request lifetime.

_For a better understanding of the scopes, [here's the associated documentation](scoped-dependencies.md)._

Here's how to configure FastAPI:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import StrEnum, auto

from fastapi import Depends, FastAPI, Request
from injection import adefine_scope, reserve_scoped_slot

class InjectionScope(StrEnum):
    LIFESPAN = auto()
    REQUEST = auto()

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with adefine_scope(InjectionScope.LIFESPAN, kind="shared"):
        yield

request_slot_key = reserve_scoped_slot(Request, InjectionScope.REQUEST)

async def request_scope(request: Request) -> AsyncIterator[None]:
    async with adefine_scope(InjectionScope.REQUEST) as scope:
        scope.set_slot(request_slot_key, request)
        yield

app = FastAPI(
    dependencies=[Depends(request_scope)],
    lifespan=lifespan,
)
```
