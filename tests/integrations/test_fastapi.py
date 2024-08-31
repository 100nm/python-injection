import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from injection import singleton
from injection.exceptions import InjectionError
from injection.integrations.fastapi import Inject

application = FastAPI()


@singleton
class Dependency: ...


@application.post("/integration", status_code=204)
async def integration_endpoint(dependency: Dependency = Inject(Dependency)):
    assert isinstance(dependency, Dependency)


@application.post("/integration-unknown-dependency")
async def integration_unknown_dependency_endpoint(
    __dependency: object = Inject(object),
):
    raise NotImplementedError


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
        with pytest.raises(InjectionError):
            client.post("/integration-unknown-dependency")
