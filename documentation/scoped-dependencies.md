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

_By default, the `kind` parameter is `"contextual"`._

> Define an asynchronous scope:

```python
from injection import adefine_scope

async def main() -> None:
    async with adefine_scope("<scope-name>"):
        ...
```

> Define a synchronous scope:

```python
from injection import define_scope

def main() -> None:
    with define_scope("<scope-name>"):
        ...
```

## MappedScope

`MappedScope` allows you to open a dependency injection scope and register values annotated with `Scoped[...]` so they 
can be retrieved by other dependencies within that scope.

### How it works

1. **Define bindings**: Create a class with fields annotated with `Scoped`.
2. **Create scope**: Instantiate `MappedScope` with a scope name.
3. **Open scope**: Use `define()` or `adefine()` context manager to register the scoped values.
4. **Access dependencies**: Other dependencies can now inject these scoped values within the context.

This is particularly useful for request-scoped dependencies in web applications, where you need to make request-specific
data available throughout the request lifecycle.

### Usage

```python
from dataclasses import dataclass
from injection import MappedScope, Scoped

class Request: ...

@dataclass
class RequestBindings:
    request: Scoped[Request]

    scope = MappedScope("request")

def process_request(request: Request) -> None:
    with RequestBindings(request).scope.define():
        # Dependencies can now access the scoped Request instance
        ...
```

### Async version

For asynchronous contexts, use `adefine`:

```python
async def process_request_async(request: Request) -> None:
    async with RequestBindings(request).scope.adefine():
        # Dependencies can now access the scoped Request instance
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

> [!IMPORTANT]
> It's preferable to use `MappedScope` instead.

Scoped slots allow you to reserve a place for an instance within a predefined scope. This ensures that injected 
functions can resolve dependencies efficiently without unnecessary recomputation. This is why the syntax can seem a 
little verbose.

Example:

```python
from injection import define_scope, reserve_scoped_slot

class Request: ...

request_slot_key = reserve_scoped_slot(Request, scope_name="request")

def process_request(request: Request) -> None:
    with define_scope("request") as scope:
        scope.set_slot(request_slot_key, request)
        # ...
```

> [!NOTE]
> You can set several slots at once with the `slot_map` method.
