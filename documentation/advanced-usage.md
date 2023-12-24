# Advanced usage

## Module

A module is an object that contains an isolated injection environment.

Modules have been designed to simplify unit test writing. So think carefully before instantiating a new one. They could
increase complexity unnecessarily if used extensively.

### Create new Module

```python
from injection import Module

my_module = Module(f"{__name__}:my_module")
```

_It's recommended to give a module name, even if this isn't mandatory._

### Basic decorators

Modules contain basic decorators. [See more.](basic-usage.md)

```python
# Injectable decorator

@my_module.injectable
class SomeInjectable:
    ...

# Singleton decorator

@my_module.singleton
class SomeSingletonInjectable:
    ...

# Inject decorator

@my_module.inject
def some_function(instance: SomeInjectable):
    ...
```

### Module interconnections

> **Use a module**

When a module is used by another module, the module's dependencies are replaced by those of the module used. 

```python
from injection import Module

module_x, module_y = Module(), Module()

class A:
    ...
    
@module_x.injectable(on=A)
class B(A):
    ...

@module_y.injectable(on=A)
class C(A):
    ...

@module_x.inject
def function(a: A):
    ...

function()  # Inject B instance
module_x.use(module_y)
function()  # Inject C instance
module_x.stop_using(module_y)
function()  # Inject B instance
```

There's also a context decorator for using a module temporarily.

```python
# Context Manager

with module_x.use_temporarily(module_y):
    # ...
    function()
    # ...

# Decorator

@module_x.use_temporarily(module_y)
def use_case():
    # ...
    function()
    # ...
```

> **Priorities**

As a module can use several modules, there's a feature for prioritizing which modules to use.

There are two priority values:
* **`LOW`**: The module concerned becomes the least important of the modules used.
* **`HIGH`**: The module concerned becomes the most important of the modules used.

The default priority is **`LOW`**.

Apply priority with `use` method:

```python
from injection import Module, ModulePriorities

module_1, module_2 = Module(), Module()

module_1.use(module_2, ModulePriorities.HIGH)
```

Apply priority with `use_temporarily` method:

```python
with module_1.use_temporarily(module_2, ModulePriorities.HIGH):
    ...
```

Change the priority of a used module:

```python
module_1.change_priority(module_2, ModulePriorities.LOW)
```

### Understand `ModuleLockError`

> **Reason**: If a module is updated while a singleton is already instantiated, this error will be raised.

#### Why?

This error exists because there's a problem with singletons. If a module is updated while a singleton is instantiated, 
there may be a problem with this instance. It may contain an obsolete dependency.

#### How to avoid it?

_First of all, make sure that all scripts containing injectables have been imported before executing the main function._

> **Tips**
> * Avoid local imports
> * Avoid singletons if not necessary 
> * Try grouping dependencies in different injection modules.

#### Unlock method

If you know what you're doing, you can delete the cached instances of all singletons using the `unlock` method:

```python
my_module.unlock()
```

### Logging

With a logging configuration that displays debug logs, you can observe everything that's happening in the modules.

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

Example:

```
DEBUG:injection.core.module:`injection:default_module` now uses `__main__:my_module`.
DEBUG:injection.core.module:`injection:default_module` has propagated an event: 1 container dependency have been updated: `__main__.A`.
DEBUG:injection.core.module:`__main__:my_module` has propagated an event: 1 container dependency have been updated: `__main__.B`.
DEBUG:injection.core.module:`injection:default_module` has propagated an event: 1 container dependency have been updated: `__main__.B`.
```
