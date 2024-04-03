from hashlib import sha256

from ...conftest import testing
from ...sources.services.hasher import AbstractHasher


@testing.singleton(on=AbstractHasher)
class SHA256Hasher(AbstractHasher):
    def hash(self, value: str) -> str:
        b = value.encode()
        return sha256(b).hexdigest()
