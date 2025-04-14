# Integrations

**Integrations make it easy to connect `python-injection` to other frameworks.**

## [FastAPI](https://github.com/fastapi/fastapi)

### Inject a dependency

Here's how to inject an instance into a FastAPI endpoint.

> Import:

```python
from injection.integrations.fastapi import Inject
```

> With **Annotated**:

```python
@app.get("/")
async def my_endpoint(
    service: Annotated[MyService, Inject(MyService)],
) -> None:
    ...
```

> Without **Annotated**:

```python
@app.get("/")
async def my_endpoint(
    service: MyService = Inject(MyService),
) -> None:
    ...
```

### Useful scopes

Two fairly common scopes in FastAPI:
* **Application lifespan scope**: associate with application lifespan.
* **Request scope**: associate with http request lifetime.

_For a better understanding of the scopes, [here's the associated documentation](scoped-dependencies.md)._

Here's how to configure FastAPI:

```python
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from enum import StrEnum, auto

from fastapi import FastAPI, Request, Response
from injection import adefine_scope, reserve_scoped_slot

class InjectionScope(StrEnum):
    LIFESPAN = auto()
    REQUEST = auto()

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with adefine_scope(InjectionScope.LIFESPAN, kind="shared"):
        yield

app = FastAPI(lifespan=lifespan)

request_slot = reserve_scoped_slot(Request, InjectionScope.REQUEST)

@app.middleware("http")
async def define_request_scope_middleware(
    request: Request,
    handler: Callable[[Request], Awaitable[Response]],
) -> Response:
    async with adefine_scope(InjectionScope.REQUEST) as scope:
        scope.set_slot(request_slot, request)
        return await handler(request)
```
