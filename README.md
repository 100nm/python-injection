# python-injection

[![CI](https://github.com/100nm/python-injection/actions/workflows/ci.yml/badge.svg)](https://github.com/100nm/python-injection)
[![PyPI - Version](https://img.shields.io/pypi/v/python-injection.svg?color=blue)](https://pypi.org/project/python-injection)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/python-injection.svg?color=blue)](https://pypistats.org/packages/python-injection)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Documentation: https://python-injection.remimd.dev

## Installation

⚠️ _Requires Python 3.12 or higher_
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
