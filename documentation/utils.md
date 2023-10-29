# Utils

## load_package

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
from injection.utils import load_package

import package

load_package(package)
```
