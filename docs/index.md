# python-injection

[![PyPI - Version](https://img.shields.io/pypi/v/python-injection.svg?color=546d78&style=for-the-badge)](https://pypi.org/project/python-injection)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/python-injection.svg?color=546d78&style=for-the-badge)](https://pypistats.org/packages/python-injection)

## Project motivations

Dependency injection in Python has long been a source of frustration. 

Existing solutions are often verbose, require extensive boilerplate, or fail to leverage Python's type hints effectively. `python-injection` was created to solve these problems once and for all by providing a simple, elegant, and powerful dependency injection framework that feels natural to Python developers.

The goal is straightforward: make dependency injection so easy that you'll wonder how you ever managed without it.

## Why choose python-injection?

- **Type-driven resolution**: Dependencies are automatically resolved using Python's type annotations.
- **Decorator-based registration**: Register your dependencies with simple, readable decorators.
- **Flexible lifetimes**: Choose from 4 type of lifetimes to match your needs:
    - **Transient**: A new instance every time
    - **Singleton**: One instance for the entire application
    - **Scoped**: One instance per scope, with context manager support
    - **Constant**: Register pre-existing values
- **Profile support**: Ability to swap certain dependencies based on a profile.
- **Pull-based instantiation**: Dependencies are only created when needed, improving startup time and resource usage.
- **Full sync/async support**: Works seamlessly with both synchronous and asynchronous code.

## Installation

Requires Python 3.12 or higher.
```bash
pip install python-injection
```

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
