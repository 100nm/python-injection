# Utils

## load_packages

Useful for put in memory injectables hidden deep within a package. Example:

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
from injection.utils import load_packages

import package

load_packages(package)
```

## load_profile

`load_profile` is an injection module initialization function based on profile name.
This is very useful when you want to use a set of dependencies based on the execution profile.

> **Note:** A profile name is equivalent to an injection module name.

For example, when I'm doing my development tests, I don't really feel like sending SMS messages.

```python
import asyncio
from abc import abstractmethod
from typing import Protocol

from injection import inject, mod, should_be_injectable, singleton
from injection.utils import load_profile

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
    main("dev")
```
