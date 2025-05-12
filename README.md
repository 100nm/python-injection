# python-injection

[![CI](https://github.com/100nm/python-injection/actions/workflows/ci.yml/badge.svg)](https://github.com/100nm/python-injection)
[![PyPI](https://img.shields.io/pypi/v/python-injection.svg?color=blue)](https://pypi.org/project/python-injection)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Fast and easy dependency injection framework.

## Installation

⚠️ _Requires Python 3.12 or higher_

```bash
pip install python-injection
```

## Motivations

1. Easy to use
2. No impact on class and function definitions
3. Easily interchangeable dependencies _(depending on the runtime environment, for example)_
4. No prerequisites

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

> ⚠️ The package isn't threadsafe, for better performance in single-threaded applications and those using `asyncio`.
> So remember to use `threading.Lock` if you're writing a multithreaded program.

* [**Basic usage**](https://github.com/100nm/python-injection/tree/prod/documentation/basic-usage.md)
* [**Scoped dependencies**](https://github.com/100nm/python-injection/tree/prod/documentation/scoped-dependencies.md)
* [**Testing**](https://github.com/100nm/python-injection/tree/prod/documentation/testing.md)
* [**Advanced usage**](https://github.com/100nm/python-injection/tree/prod/documentation/advanced-usage.md)
* [**Loaders**](https://github.com/100nm/python-injection/tree/prod/documentation/loaders.md)
* [**Entrypoint**](https://github.com/100nm/python-injection/tree/prod/documentation/entrypoint.md)
* [**Integrations**](https://github.com/100nm/python-injection/tree/prod/documentation/integrations.md)
* [**Concrete example**](https://github.com/100nm/python-injection-example)
