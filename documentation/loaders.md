# Loaders

## PythonModuleLoader

Useful for put in memory injectables hidden deep within a package.

```
package
├── sub_package
│   ├── __init__.py
│   └── module2.py
│       └── class Injectable2
├── __init__.py
└── module1.py
    └── class Injectable1
```

To load Injectable1 and Injectable2 into memory you can do the following:

```python
# Imports
from injection.loaders import PythonModuleLoader
import package
```

```python
def predicate(module_name: str) -> bool:
    # logic to determine whether the module should be imported or not
    return True

PythonModuleLoader(predicate).load(package)
```

### Factory methods

* `from_keywords`

Automatically imports modules whose Python script contains one of the keywords passed in parameter.

```python
PythonModuleLoader.from_keywords("# Auto-import").load(package)
```

* `startswith`

Automatically imports modules whose Python script name begins with one of the prefixes passed in parameter.

```python
profile: str = ...
PythonModuleLoader.startswith(f"{profile}_").load(package)
```

* `endswith`

Automatically imports modules whose Python script name ends with one of the suffixes passed in parameter.

```python
profile: str = ...
PythonModuleLoader.endswith(f"_{profile}").load(package)
```

## load_packages

`load_packages` is a simplified version of `PythonModuleLoader`.

```python
from injection.loaders import load_packages

import package

load_packages(package)
```

## load_profile

`load_profile` is an injection module initialization function based on profile name.
This is very useful when you want to use a set of dependencies based on the execution profile.

> [!NOTE]
> A profile name is equivalent to an injection module name.

For example, when I'm doing my development tests, I don't really feel like sending SMS messages.

```python
import asyncio
from abc import abstractmethod
from typing import Protocol

from injection import inject, mod, should_be_injectable, singleton
from injection.loaders import load_profile

@should_be_injectable
class SMSService(Protocol):
    @abstractmethod
    async def send(self, phone_number: str, message: str):
        raise NotImplementedError

@singleton(on=SMSService)
class ConcreteSMSService(SMSService):
    async def send(self, phone_number: str, message: str):
        """
        Concrete implementation of `SMSService.send`.
        """

@mod("dev").singleton(on=SMSService)
class ConsoleSMSService(SMSService):
    async def send(self, phone_number: str, message: str):
        print(f"SMS send to `{phone_number}`:\n{message}")

@inject
async def send_sms(service: SMSService):
    await service.send(
        phone_number="+33 6 00 00 00 00",
        message="Hello world!",
    )

def main(profile_name: str = None, /):
    if profile_name is not None:
        load_profile(profile_name)

    asyncio.run(send_sms())

if __name__ == "__main__":
    main("dev")  # One could imagine the profile name being transmitted via an environment variable or CLI parameter
```

## ProfileLoader

_This is a slightly more complete version of `load_profile`._

If you use modules as subsets of dependencies, this class will make your life easier.

It is recommended to use a single instance of `ProfileLoader` to avoid unexpected behavior. If it exists, this instance
must be passed to `entrypointmaker` and `load_test_profile`.

Here's an example of its use:

```python
from injection import mod
from injection.loaders import ProfileLoader

profile_loader = ProfileLoader(
    {
        mod().name: ["global"],
        "dev": ["stub", "global"],
        "test": ["stub", "global"],
        "stub": ["global"]
    }
)

# Ensures that dependent modules are used properly.
# If `init` isn't called, it will be automatically called with `load`.
profile_loader.init()

# Load `dev` profile.
profile_loader.load("dev")
```

> [!NOTE]
> `load` can also be used as a context manager:
>
> ```python
> with profile_loader.load("<profile-name>"):
>     ...
> ```
