from abc import ABC, abstractmethod
from uuid import UUID, uuid4

from injection import singleton


class AbstractUUIDService(ABC):
    @abstractmethod
    def generate(self) -> UUID:
        raise NotImplementedError


@singleton(on=AbstractUUIDService)
class UUIDService(AbstractUUIDService):
    def generate(self) -> UUID:
        return uuid4()
