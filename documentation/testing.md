# Testing

_To create your test injection module, I recommend you first read [this](advanced-usage.md#module)._

Example of a [pytest](https://github.com/pytest-dev/pytest) fixture that can be used to replace dependencies during test execution:

```python
# conftest.py

import pytest
from injection import ModulePriorities, default_module


@pytest.fixture(scope="function", autouse=True)
def injection_fixture():
    with default_module.use_temporarily(test_module, ModulePriorities.HIGH):
        yield
        default_module.unlock()
```
