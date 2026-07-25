# [FastAPI](https://github.com/fastapi/fastapi)

## Inject a dependency

Here's how to inject an instance into a FastAPI endpoint.
```python
from injection.ext.fastapi import Inject


@app.get("/")
async def endpoint(dependency: Inject[Dependency]): ...
```

## Useful scopes

Two fairly common scopes in FastAPI:

- **Application lifespan scope**: associate with application lifespan.
- **Request scope**: associate with http request lifetime.

_For a better understanding of the scopes, [here's the associated documentation](../guides/scopes.md)._

Here's how to configure FastAPI:
```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import StrEnum, auto

from fastapi import Depends, FastAPI, Request
from injection import MappedScope, adefine_scope


class InjectionScope(StrEnum):
    LIFESPAN = auto()
    REQUEST = auto()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with adefine_scope(InjectionScope.LIFESPAN, kind="shared"):
        yield


@dataclass
class FastAPIRequestBindings:
    # You can use any bindings; Request is just an example.
    request: Request

    scope = MappedScope(InjectionScope.REQUEST)


async def request_scope(request: Request) -> AsyncIterator[None]:
    async with FastAPIRequestBindings(request).scope.adefine():
        yield


app = FastAPI(
    dependencies=[Depends(request_scope)],
    lifespan=lifespan,
)
```
