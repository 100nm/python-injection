# [Pytest](https://github.com/pytest-dev/pytest)

You can simplify test setup by creating a pytest fixture that automatically loads test dependencies. Add this fixture to your `conftest.py` file to make it available across all your tests.

## Fixture
```python
# conftest.py

import pytest
from injection.testing import load_test_profile

@pytest.fixture(scope="function", autouse=True)
def setup_test_dependencies():
    with load_test_profile():
        yield
```

The `autouse=True` parameter ensures this fixture runs automatically for every test without needing to explicitly reference it.

!!! note
    If you're using a [`ProfileLoader`](../guides/profiles.md#profileloader), pass it to `load_test_profile`.

With this setup, all your tests automatically have access to test dependencies without any additional configuration.
