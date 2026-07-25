# Test dependencies

Testing often requires replacing real dependencies with mocks, stubs, or test-specific implementations. The `injection.testing` module provides dedicated registration decorators that work alongside your regular dependencies without interfering with production code.

## Activating test dependencies

Before using test dependencies, you must activate the test profile using `load_test_profile`:
```python
from injection.testing import load_test_profile

load_test_profile()
```

If you're using a [`ProfileLoader`](../guides/profiles.md#profileloader), pass it to `load_test_profile`:
```python
from injection.loaders import ProfileLoader
from injection.testing import load_test_profile

profile_loader = ProfileLoader(...)

load_test_profile(profile_loader)
```

`load_test_profile` can also be used as a context manager to automatically unload the test profile after test complete:
```python
from injection.testing import load_test_profile

with load_test_profile():
    # Test dependencies are active here
    run_test()

# Test profile is unloaded, cache is cleared
```

## Test-specific decorators

All the registration decorators you've seen earlier have test equivalents in `injection.testing`:
```python
from injection.testing import (
    set_test_constant,
    test_constant,
    test_injectable,
    test_scoped,
    test_singleton,
)
```

These decorators work exactly like their production counterparts but register dependencies in a separate test registry.

### Using test decorators

#### test_injectable

```python
from injection.testing import test_injectable


@test_injectable(on=AbstractDependency)
class MockDependency(AbstractDependency): ...
```

#### test_singleton

```python
from injection.testing import test_singleton


@test_singleton(on=AbstractDependency)
class MockDependency(AbstractDependency): ...
```

#### set_test_constant

```python
from injection.testing import set_test_constant

type APIKey = str

test_api_key = set_test_constant("test_key_123", APIKey, alias=True)
```

#### test_constant

```python
from dataclasses import dataclass
from injection import constant
from injection.testing import test_constant
from os import environ


@dataclass(frozen=True)
class Settings:
    api_key: str
    debug: bool


@constant
def _settings_factory() -> Settings:
    return Settings(environ["API_KEY"], debug=False)


@test_constant
def _settings_test_factory() -> Settings:
    return Settings("test_key_123", debug=True)
```

#### test_scoped

```python
from injection.testing import test_scoped


@test_scoped("<scope_name>", on=AbstractDependency)
class MockDependency(AbstractDependency): ...
```

## How test dependencies work

Test dependencies are registered in a separate registry and **take precedence over production dependencies** when tests are running. This means:

- You can override production implementations with test versions
- Production code remains unchanged
- Test dependencies are isolated from production dependencies
- No need to modify your production registration code

!!! tip "Best practice"
    Register test dependencies in your test files or in a dedicated test configuration module. This keeps test setup close to your tests and makes it clear which dependencies are being mocked.
