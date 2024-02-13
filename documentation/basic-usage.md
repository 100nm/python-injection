# Basic usage

## Create an injectable

> **Note**: If the class needs dependencies, these will be resolved when the instance is retrieved.

If you wish to inject a singleton, use `singleton` decorator.

```python
from injection import singleton

@singleton
class Singleton:
    """ class implementation """
```

If you wish to inject a new instance each time, use `injectable` decorator.

```python
from injection import injectable

@injectable
class Injectable:
    """ class implementation """
```

If you have a constant (such as a global variable) and wish to register it as an injectable, use `set_constant`
function.

```python
from injection import set_constant

app = set_constant(Application())
```

## Inject an instance

To inject one or several instances, use `inject` decorator.
_Don't forget to annotate type of parameter to inject._

```python
from injection import inject

@inject
def my_function(instance: Injectable):
    """ function implementation """
```

If `inject` decorates a class, it will be applied to the `__init__` method.
_Especially useful for dataclasses:_

> **Note**: Doesn't work with Pydantic `BaseModel` because the signature of the `__init__` method doesn't contain the
> dependencies.

```python
from dataclasses import dataclass

from injection import inject

@inject
@dataclass
class DataClass:
    instance: Injectable = ...
```

## Get an instance

_Example with `get_instance` function:_

```python
from injection import get_instance

instance = get_instance(Injectable)
```

_Example with `get_lazy_instance` function:_

```python
from injection import get_lazy_instance

lazy_instance = get_lazy_instance(Injectable)
# ...
instance = ~lazy_instance
```

## Inheritance

In the case of inheritance, you can use the decorator parameter `on` to link the injection to one or several other
classes.

**Warning: if the child class is in another file, make sure that file is imported before injection.**
[_See `load_package` function._](utils.md#load_package)

_Example with one class:_

```python
from injection import singleton

class A:
    ...

@singleton(on=A)
class B(A):
    ...
```

_Example with several classes:_

```python
from injection import singleton

class A:
    ...

class B(A):
    ...

@singleton(on=(A, B))
class C(B):
    ...
```

If a class is registered in a package and you want to override it, there is the `override` parameter:

```python
@singleton
class A:
    ...

# ...

@singleton(on=A, override=True)
class B(A):
    ...
```

## Recipes

A recipe is a function that tells the injector how to construct the instance to be injected. It is important to specify 
the return type annotation when defining the recipe.

```python
from injection import singleton

@singleton
def my_recipe() -> Singleton:
    """ recipe implementation """
```
