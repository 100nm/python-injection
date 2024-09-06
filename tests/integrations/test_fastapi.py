import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from injection import injectable
from injection.exceptions import InjectionError
from injection.integrations.fastapi import Inject

application = FastAPI()


@injectable
class Dependency: ...


def some_dependency(
    dependency: Dependency = Inject(Dependency),
) -> Dependency:
    return dependency


@application.post("/integration", status_code=204)
async def integration_endpoint(
    dependency: Dependency = Inject(Dependency),
    inner_dependency: Dependency = Depends(some_dependency),
):
    assert isinstance(dependency, Dependency)
    assert dependency is inner_dependency


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
