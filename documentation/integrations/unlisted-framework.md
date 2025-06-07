# What if my framework isn't listed?

You like `python-injection`, but your framework isn't officially supported? Don't worry, there are still several ways 
to make it work.

## If your framework doesn't inspect function signatures

In most cases, if your framework doesn't inspect function signatures, you can use the `@inject` decorator without any 
issues.

## If your framework inspects function signatures

If your framework inspects function signatures, things get a bit trickier. This is because you'll need to **perform 
dependency injection first, then call the function**, which isn't always compatible with how decorators work on regular 
functions.

To solve this, you can define a class with a `__call__` method (where dependencies are injected), and use the 
`asfunction` decorator to turn it into a function.

The resulting function will have the same signature as the `__call__` method, but without the `self` parameter.

Example:

```python
from typing import NamedTuple
from injection import asfunction

@asfunction
class do_something(NamedTuple):
    service: MyService

    def __call__(self):
        self.service.do_work()
```

## Need more than these tools?

[**Feel free to start a discussion here.**](https://github.com/100nm/python-injection/discussions/new/choose)
