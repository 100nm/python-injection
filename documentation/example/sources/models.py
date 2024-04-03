from uuid import UUID

from pydantic import BaseModel, SecretStr, field_serializer


class User(BaseModel):
    id: UUID
    username: str
    password: SecretStr

    @field_serializer("password")
    def password_serializer(self, value: SecretStr) -> str:
        return value.get_secret_value()
