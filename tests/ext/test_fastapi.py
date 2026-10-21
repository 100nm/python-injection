from collections.abc import AsyncIterator
from typing import Annotated

import pytest
from fastapi import FastAPI, status
from httpx2 import ASGITransport, AsyncClient

from injection._core.module import Module, mod
from injection.ext.fastapi import Inject


class A: ...


class B: ...


@pytest.fixture
async def client(module: Module) -> AsyncIterator[AsyncClient]:
    module.injectable(A)
    explicit_module = Module()
    explicit_module.injectable(B)
    app = FastAPI()

    @app.get("/default-module")
    async def get_from_default_module(a: Inject[A]) -> str:
        return type(a).__name__

    @app.get("/explicit-module")
    async def get_from_explicit_module(
        b: Annotated[B, Inject(B, module=explicit_module, threadsafe=True)],
    ) -> str:
        return type(b).__name__

    @app.get("/unknown-dependency")
    async def get_unknown_dependency(value: Inject[int]) -> bool:
        return value is NotImplemented

    transport = ASGITransport(app=app)

    with mod().use_temporarily(module):
        async with AsyncClient(base_url="http://test", transport=transport) as client:
            yield client


class TestInject:
    async def test_getitem_with_registered_class_returns_annotation(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.get("/default-module")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == "A"

    async def test_getitem_without_injectable_returns_annotation(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.get("/unknown-dependency")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() is True

    async def test_call_with_module_returns_dependency(
        self,
        client: AsyncClient,
    ) -> None:
        response = await client.get("/explicit-module")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == "B"
