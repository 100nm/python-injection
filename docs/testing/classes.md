# Writing test classes

Test frameworks like pytest and unittest don't allow custom `__init__` methods in test classes. To inject dependencies into test classes, use `LazyInstance` for sync dependencies and `aget_lazy_instance` for async dependencies.

## Using LazyInstance

The `LazyInstance` descriptor resolves dependencies on access:
```python
from injection import LazyInstance

class TestFeature:
    dependency = LazyInstance(Dependency)
    
    def test_something(self):
        result = self.dependency.some_method()
        assert result == expected_value
```

## Using aget_lazy_instance for async

For async dependencies, use `aget_lazy_instance` which returns an awaitable:
```python
from injection import aget_lazy_instance

class TestAsyncFeature:
    lazy_dependency = aget_lazy_instance(AsyncDependency)
    
    async def test_something(self):
        dependency = await self.lazy_dependency
        result = await dependency.some_method()
        assert result == expected_value
```

!!! tip
    Use `LazyInstance` for sync dependencies (cleaner syntax) and `aget_lazy_instance` only when you need async dependencies.

!!! warning
    `LazyInstance` resolves the dependency on **every access**. With transient dependencies, you get a new instance each time. With singletons, you get the same instance.
