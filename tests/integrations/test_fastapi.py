import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from injection import singleton
from injection.integrations.fastapi import Inject

application = FastAPI()


@singleton
class Dependency: ...


@application.post("/integration", status_code=204)
async def integration_endpoint(dependency: Dependency | None = Inject(Dependency)):
    assert isinstance(dependency, Dependency)


class TestFastAPIIntegration:
    @pytest.fixture(scope="class")
    def client(self) -> TestClient:
        return TestClient(application)

    def test_fastapi_integration_with_success(self, client):
        response = client.post("/integration")
        assert response.status_code == 204
