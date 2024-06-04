from collections.abc import AsyncIterator

import pytest
from blacksheep import Application, Response
from blacksheep.server.controllers import APIController, post
from blacksheep.testing import TestClient

from injection import singleton
from injection.integrations.blacksheep import InjectionServices

application = Application(
    services=InjectionServices(),
)


@singleton
class Dependency:
    pass


class Controller(APIController):
    def __init__(self, dependency: Dependency):
        self.__dependency = dependency

    @classmethod
    def class_name(cls) -> str:
        return "tests"

    @post("/integration")
    async def test_integration(self) -> Response:
        assert isinstance(self.__dependency, Dependency)
        return self.no_content()


class TestBlackSheepIntegration:
    @pytest.fixture(scope="class")
    async def client(self) -> AsyncIterator[TestClient]:
        await application.start()
        yield TestClient(application)
        await application.stop()

    async def test_blacksheep_integration_with_success(self, client):
        response = await client.post("/api/tests/integration")
        assert response.status == 204
