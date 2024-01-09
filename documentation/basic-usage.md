# Basic usage

## Create an injectable

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

> **Note**: If the class needs dependencies, these will be resolved when the instance is retrieved.

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

```python
from dataclasses import dataclass

from injection import inject

@inject
@dataclass
class DataClass:
    instance: Injectable = ...
```

> **Note**: Doesn't work with Pydantic `BaseModel` because the signature of the `__init__` method doesn't contain the
> dependencies.

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

## Recipes

A recipe is a function that tells the injector how to construct the instance to be injected. It is important to specify 
the return type annotation when defining the recipe.

```python
from injection import singleton

@singleton
def my_recipe() -> Singleton:
    """ recipe implementation """
```
