from hashlib import sha256

from injection.testing import test_singleton

from ...sources.services.hasher import AbstractHasher


@test_singleton(on=AbstractHasher)
class SHA256Hasher(AbstractHasher):
    def hash(self, value: str) -> str:
        b = value.encode()
        return sha256(b).hexdigest()
