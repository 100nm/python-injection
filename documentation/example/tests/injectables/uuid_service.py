from uuid import UUID

from faker import Faker

from ...conftest import testing
from ...sources.services.uuid_service import AbstractUUIDService


@testing.singleton(on=AbstractUUIDService)
class FakeUUIDService(AbstractUUIDService):
    def __init__(self):
        self.__faker = Faker()

    def generate(self) -> UUID:
        return UUID(self.__faker.uuid4())
