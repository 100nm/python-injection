# python-injection

[![CI](https://github.com/100nm/python-injection/actions/workflows/ci.yml/badge.svg)](https://github.com/100nm/python-injection)
[![PyPI - Version](https://img.shields.io/pypi/v/python-injection.svg?color=blue)](https://pypi.org/project/python-injection)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/python-injection.svg?color=blue)](https://pypistats.org/packages/python-injection)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Installation

⚠️ _Requires Python 3.12 or higher_

```bash
pip install python-injection
```

## Features

* Automatic dependency resolution based on type hints.
* Support for multiple dependency lifetimes: `transient`, `singleton`, `constant`, and `scoped`.
* Works seamlessly in both `async` and `sync` environments.
* Separation of dependency sets using modules.
* Runtime switching between different sets of dependencies.
* Centralized setup logic using entrypoints.
* Built-in type annotation for easy integration with [`FastAPI`](https://github.com/fastapi/fastapi).
* Lazy dependency resolution for optimized performance.

## Motivations

1. Easy to use
2. No impact on class and function definitions
3. No tedious configuration

## Quick start

Simply apply the decorators and the package takes care of the rest.

```python
from injection import injectable, inject, singleton

@singleton
class Printer:
    def __init__(self):
        self.history = []

    def print(self, message: str):
        self.history.append(message)
        print(message)

@injectable
class Service:
    def __init__(self, printer: Printer):
        self.printer = printer

    def hello(self):
        self.printer.print("Hello world!")

@inject
def main(service: Service):
    service.hello()

if __name__ == "__main__":
    main()
```

## Resources

> ⚠️ The package isn't threadsafe by default, for better performance in single-threaded applications and those using
> `asyncio`.
> 
> Non-threadsafe functions are those that resolve dependencies or define scopes. They all come with an optional 
> parameter `threadsafe`.
> 
> You can set `PYTHON_INJECTION_THREADSAFE=1` in environment variables to make the package fully threadsafe. The 
> environment variable is resolved at the **Python module level**, so be careful if the variable is defined dynamically.

* [**Basic usage**](https://github.com/100nm/python-injection/tree/prod/documentation/basic-usage.md)
* [**Scoped dependencies**](https://github.com/100nm/python-injection/tree/prod/documentation/scoped-dependencies.md)
* [**Testing**](https://github.com/100nm/python-injection/tree/prod/documentation/testing.md)
* [**Advanced usage**](https://github.com/100nm/python-injection/tree/prod/documentation/advanced-usage.md)
* [**Loaders**](https://github.com/100nm/python-injection/tree/prod/documentation/loaders.md)
* [**Entrypoint**](https://github.com/100nm/python-injection/tree/prod/documentation/entrypoint.md)
* [**Integrations**](https://github.com/100nm/python-injection/tree/prod/documentation/integrations)
  * [**FastAPI**](https://github.com/100nm/python-injection/tree/prod/documentation/integrations/fastapi.md)
  * [**What if my framework isn't listed?**](https://github.com/100nm/python-injection/tree/prod/documentation/integrations/unlisted-framework.md)
* [**Concrete example**](https://github.com/100nm/python-injection-example)
