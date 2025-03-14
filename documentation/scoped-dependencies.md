# Scoped dependencies

The scoped dependencies were created for two reasons:
* To have dependencies that have a defined lifespan.
* To be able to open and close things in a dependency recipe.

## Best practices

* Avoid making a singleton dependent on a scoped dependency.
* Define scope names in a `StrEnum`.

## Scope

The scope is responsible for instance persistence and for cleaning up when it closes.

There are two kinds of scopes:
* **Contextual**: All threads have access to a different scope (based on [contextvars](https://docs.python.org/3.13/library/contextvars.html)).
* **Shared**: All threads have access to the same scope.

First of all, the scope must be defined:

_By default, the `shared` parameter is `False`._

> Define an asynchronous scope:

```python
from injection import adefine_scope

async def main() -> None:
    async with adefine_scope("<scope-name>", shared=True):
        ...
```

> Define a synchronous scope:

```python
from injection import define_scope

def main() -> None:
    with define_scope("<scope-name>", shared=True):
        ...
```

## Register a scoped dependencies

`@scoped` works exactly like `@injectable`, it just has extra features.

### "contextmanager-like" recipes

_Anything after the `yield` keyword will be executed when the scope is closed._

> Asynchronous (asynchronous scope required):

```python
from collections.abc import AsyncIterator
from injection import scoped

class Client:
    async def open_connection(self) -> None: ...
    
    async def close_connection(self) -> None: ...

@scoped("<scope-name>")
async def client_recipe() -> AsyncIterator[Client]:
    # On resolving dependency
    client = Client()
    await client.open_connection()
    
    try:
        yield client
    finally:
        # On scope close
        await client.close_connection()
```

> Synchronous:

```python
from collections.abc import Iterator
from injection import scoped

class Client:
    def open_connection(self) -> None: ...
    
    def close_connection(self) -> None: ...

@scoped("<scope-name>")
def client_recipe() -> Iterator[Client]:
    # On resolving dependency
    client = Client()
    client.open_connection()
    
    try:
        yield client
    finally:
        # On scope close
        client.close_connection()
```

### Scoped slots

Scoped slots allow you to reserve a place for an instance within a predefined scope. This ensures that injected 
functions can resolve dependencies efficiently without unnecessary recomputation. This is why the syntax can seem a 
little verbose.

Example:

```python
from injection import define_scope, reserve_scoped_slot

class Request: ...

request_slot = reserve_scoped_slot(Request, scope_name="request")

def process_request(request: Request) -> None:
    with define_scope("request"):
        request_slot.set(request)
        # ...
```
