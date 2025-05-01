import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from injection import injectable
from injection.ext.fastapi import Inject

application = FastAPI()


@injectable
class Dependency: ...


@application.post("/integration", status_code=204)
async def integration_endpoint(dependency: Dependency = Inject(Dependency)):
    assert isinstance(dependency, Dependency)


@application.post("/integration-unknown-dependency", status_code=204)
async def integration_unknown_dependency_endpoint(dependency: object = Inject(object)):
    assert dependency is NotImplemented


class TestFastAPIIntegration:
    @pytest.fixture(scope="class")
    def client(self) -> TestClient:
        return TestClient(application)

    def test_fastapi_integration_with_success(self, client):
        response = client.post("/integration")
        assert response.status_code == 204

    def test_fastapi_integration_with_unknown_dependency_raise_injection_error(
        self,
        client,
    ):
        response = client.post("/integration-unknown-dependency")
        assert response.status_code == 204
