# Testing

## Test configuration

Here is the [Pytest](https://github.com/pytest-dev/pytest) fixture for using test injectables on all tests:

```python
# conftest.py

import pytest
from injection.testing import use_test_injectables

@pytest.fixture(scope="session", autouse=True)
def autouse_test_injectables():
    # Ensure that test injectables have been imported here
    
    with use_test_injectables():
        yield
```

## Register a test injectable

> **Notes**
> * Test injectables replace conventional injectables if they are registered on the same type.
> * A test injectable can't depend on a conventional injectable.

`@singleton` equivalent for testing:


```python
from injection.testing import test_singleton

@test_singleton
class ServiceA:
    """ class implementation """
```

`@injectable` equivalent for testing:


```python
from injection.testing import test_injectable

@test_injectable
class ServiceB:
    """ class implementation """
```

`set_constant` equivalent for testing:

```python
from injection.testing import set_test_constant

class ServiceC:
    """ class implementation """

service_c = ServiceC()
set_test_constant(service_c)
```
