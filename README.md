# python-injection

[![PyPI - Version](https://shieldcn.dev/pypi/v/python-injection.svg?color=3775A9&size=xs&variant=secondary)](https://pypi.org/project/python-injection)
[![PyPI - Downloads](https://shieldcn.dev/pypi/dm/python-injection.svg?color=3775A9&size=xs&variant=secondary)](https://pypistats.org/packages/python-injection)
[![GitHub Stars](https://shieldcn.dev/github/stars/100nm/python-injection.svg?size=xs&variant=secondary)](https://github.com/100nm/python-injection/stargazers)
[![CI](https://shieldcn.dev/github/ci/100nm/python-injection.svg?size=xs&variant=secondary&workflow=ci.yml)](https://github.com/100nm/python-injection/actions/workflows/ci.yml)
[![Ruff](https://shieldcn.dev/badge/code_style-Ruff-261230.svg?logo=ruff&size=xs&variant=secondary)](https://github.com/astral-sh/ruff)

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
