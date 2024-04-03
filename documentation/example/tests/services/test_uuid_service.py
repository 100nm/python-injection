from uuid import UUID

from injection import inject

from ...sources.services.uuid_service import UUIDService


class TestUUIDService:
    @classmethod
    def setup_class(cls):
        cls.init_dependencies()

    @classmethod
    @inject
    def init_dependencies(cls, uuid_service: UUIDService):
        cls.uuid_service = uuid_service

    def test_generate_with_success_return_uuid(self):
        uuid = self.uuid_service.generate()

        assert isinstance(uuid, UUID)
