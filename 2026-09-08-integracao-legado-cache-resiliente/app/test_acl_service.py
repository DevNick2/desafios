import json

import httpx
import pytest

from .ACLService import ACLService
from .CacheService import CacheService

""" Novo caso de teste, adicionar uma linha vazia
    ao cache, um dict vazio, e ver como retorna
    nos cenários com e sem o desserializer
"""


@pytest.fixture(scope="session", autouse=True)
def setup():
    cacheService = CacheService()
    cacheService.instance.flushdb()


@pytest.fixture(scope="session")
def products_list_json():
    with open("data/products.json", "r", encoding="utf8") as file:
        return json.load(file)


@pytest.fixture(scope="session")
def products_list_stock():
    with open("data/legacy_stock.json", "r", encoding="utf8") as file:
        return json.load(file)


@pytest.fixture(scope="session")
def products_list_with_stock(
    products_list_json, products_list_stock
) -> list[dict]:
    mockProductsWithStock: list[dict] = []

    for item in products_list_json:
        if item["id"] not in products_list_stock:
            continue

        mockProductsWithStock.append(
            {**item, "stock": products_list_stock[item["id"]]}
        )

    return mockProductsWithStock


async def test_products_list_returned_success(products_list_with_stock):
    # Arrange
    aclService = ACLService(0.0, 0.0, 0.0)

    # Act
    productsList = await aclService.backoff(2, 2)

    # Assert
    assert productsList == products_list_with_stock


async def test_products_list_returned_is_adapter(
    monkeypatch,
    products_list_with_stock,
):
    # Arrange
    aclService = ACLService(0.0, 0.0, 0.0)

    async def mock_backoff_response(*args) -> list[dict]:
        return products_list_with_stock

    monkeypatch.setattr(aclService, "backoff", mock_backoff_response)

    # Act
    productsList = await aclService.list_products()

    # Assert
    assert productsList == aclService.adapter(products_list_with_stock)


async def test_error_when_try_get_products_list(monkeypatch):
    # Arrange
    aclService = ACLService(0.0, 0.0, 0.0)

    def mock_backoff_response_error(*args):
        raise ConnectionError("Legacy connection failed!")

    monkeypatch.setattr(aclService, "backoff", mock_backoff_response_error)

    # Act
    # Assert
    with pytest.raises(ConnectionError) as exec_info:
        await aclService.list_products()

    assert exec_info.type is ConnectionError
    assert exec_info.value.args[0] == "Legacy connection failed!"


async def test_health_check_success(monkeypatch):
    # Arrange
    aclService = ACLService(0.0, 0.0, 0.0)

    def mock_http_request_response():
        return httpx.Response(
            404, content=b'{"response": "product not found in legacy system"}'
        )

    monkeypatch.setattr(httpx, "get", mock_http_request_response)

    # Act
    healthCheck = await aclService.health_check()

    # Assert
    assert healthCheck is True


async def test_health_check_fail(monkeypatch):
    # Arrange
    aclService = ACLService(0.0, 0.0, 0.0)

    async def mock_http_request_response(*args):
        return httpx.Response(
            500, request=httpx.Request("get", url=""), content=b"{}"
        )

    monkeypatch.setattr(
        aclService.http_client, "get", mock_http_request_response
    )

    # Act
    with pytest.raises(ConnectionError) as exec_info:
        await aclService.health_check()

    # Assert
    assert exec_info.type is ConnectionError
    assert exec_info.value.args[0] == "Legacy connection failed!"
