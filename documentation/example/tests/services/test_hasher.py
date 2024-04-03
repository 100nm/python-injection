from injection import inject

from ...sources.services.hasher import Argon2Hasher


class TestArgon2Hasher:
    @classmethod
    def setup_class(cls):
        cls.init_dependencies()

    @classmethod
    @inject
    def init_dependencies(cls, hasher: Argon2Hasher):
        cls.hasher = hasher

    def test_hash_with_success_return_str(self):
        value = "root"
        h = self.hasher.hash(value)

        assert h != value
        assert h.startswith("$argon2id$")
