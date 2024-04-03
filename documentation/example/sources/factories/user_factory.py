from typing import Any

from injection import singleton

from ..models import User
from ..services.hasher import AbstractHasher
from ..services.uuid_service import AbstractUUIDService


@singleton
class UserFactory:
    def __init__(self, uuid_service: AbstractUUIDService, hasher: AbstractHasher):
        self.__uuid_service = uuid_service
        self.__hasher = hasher

    def build(self, data: dict[str, Any]) -> User:
        data.setdefault("id", self.__uuid_service.generate())

        if password := data.get("password"):
            data["password"] = self.__hasher.hash(password)

        return User.model_validate(data)
