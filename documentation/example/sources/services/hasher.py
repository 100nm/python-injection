from abc import ABC, abstractmethod

from argon2 import PasswordHasher

from injection import singleton


class AbstractHasher(ABC):
    @abstractmethod
    def hash(self, value: str) -> str:
        raise NotImplementedError


@singleton(on=AbstractHasher)
class Argon2Hasher(AbstractHasher):
    def __init__(self):
        self.__hasher = PasswordHasher()

    def hash(self, value: str) -> str:
        return self.__hasher.hash(value)
