# Injection

[![CI](https://github.com/soon-app/injection/actions/workflows/ci.yml/badge.svg)](https://github.com/soon-app/injection)
[![PyPI](https://badge.fury.io/py/python-injection.svg)](https://pypi.org/project/python-injection/)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Fast and easy dependency injection framework.

## Quick start

⚠️ _Requires Python 3.10 or higher_

```bash
pip install python-injection
```

## How to use

### Create an injectable

If you wish to inject a singleton, use `unique` decorator.

```python
from injection import unique

@unique
class MyClass:
    """ class implementation """
```

If you wish to inject a new instance each time, use `new` decorator.

```python
from injection import new

@new
class MyClass:
    """ class implementation """
```

### Inject an instance

To inject one or several instances, use `inject` decorator.
_Don't forget to annotate type of parameter to inject._

```python
from injection import inject

@inject
def my_function(instance: MyClass):
    """ function implementation """
```

### Inheritance

In the case of inheritance, you can use the decorator parameters `reference` or `references` to link the injection to 
one or several other classes.

**Warning: if the child class is in another file, make sure that file is imported before injection.**
[_See `load_package` function._](#load_package)

_`reference` parameter example:_

```python
from injection import unique

class A:
    ...

@unique(reference=A)
class B(A):
    ...
```

_`references` parameter example:_

```python
from injection import unique

class A:
    ...

class B(A):
    ...

@unique(references=(A, B))
class C(B):
    ...
```

### Recipes

A recipe is a function that tells the injector how to construct the instance to be injected. It is important to specify 
the reference class(es) when defining the recipe.

```python
from injection import unique

@unique(reference=MyClass)
def my_recipe() -> MyClass:
    """ recipe implementation """
```

## Utils

### load_package

Useful for put in memory injectables hidden deep within a package. Example:

```
package
├── sub_package
│   ├── __init__.py
│   └── module2.py
│       └── class Injectable2
├── __init__.py
└── module1.py
    └── class Injectable1
```

To load Injectable1 and Injectable2 into memory you can do the following:

```python
from injection.utils import load_package

import package

load_package(package)
```
