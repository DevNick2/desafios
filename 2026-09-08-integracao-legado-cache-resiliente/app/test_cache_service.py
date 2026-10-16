import json

import pytest
from pydantic import TypeAdapter

from .ACLService import BaseModel, Product
from .CacheService import CacheService


class ProductStock(BaseModel):
    available_stock: int
    product_id: str


class ProductWithStock(BaseModel):
    id: str
    name: str
    category: str
    base_price: float
    stock: int


@pytest.fixture(scope="session", autouse=True)
def setup():
    cacheService = CacheService()
    cacheService.instance.flushdb()


@pytest.fixture
def products_list_json():
    with open("data/products.json", "r", encoding="utf8") as file:
        return TypeAdapter(list[Product]).validate_python(json.load(file))


@pytest.fixture
def products_list_stock():
    with open("data/legacy_stock.json", "r", encoding="utf8") as file:
        products_stock = json.load(file)
        products_stock_dict = {}

        for key in products_stock:
            products_stock_dict["product_id"] = key
            products_stock_dict["available_stock"] = products_stock[key]

        return TypeAdapter(ProductStock).validate_python(products_stock_dict)


def test_deserializer_parameter():
    # Arrange
    mockProduct = {
        "id": "P01",
        "name": "Smartphone X200",
        "category": "ELECTRONICS",
        "base_price": 1899.90,
        "stock": 15,
    }
    # Act
    cacheService = CacheService(
        deserialize=lambda data: TypeAdapter(ProductWithStock).validate_python(
            data
        )
    )

    cacheService.set_key(f"product:{mockProduct['id']}", mockProduct)
    product = cacheService.get_key(
        f"product:{mockProduct['id']}",
        value_type="dict",
        deserialize=lambda data: TypeAdapter(ProductWithStock).validate_python(
            data
        ),
    )
    # Assert
    assert isinstance(product, ProductWithStock)
    assert isinstance(product.stock, int)


def test_without_deserializer_parameter():
    # Arrange
    mockProduct = {
        "id": "P01",
        "name": "Smartphone X200",
        "category": "ELECTRONICS",
        "base_price": 1899.90,
        "stock": 15,
    }
    # Act
    cacheService = CacheService()

    cacheService.set_key(f"product:{mockProduct['id']}", mockProduct)
    product = cacheService.get_key(
        f"product:{mockProduct['id']}",
        value_type="dict",
    )
    # Assert

    assert isinstance(product, dict)
    assert isinstance(product["stock"], str)


def test_set_dict_key(products_list_json, products_list_stock):
    # Arrange
    cacheService = CacheService()

    mockProductsWithStock: list[dict] = []

    for item in products_list_json:
        if item.id not in products_list_stock:
            continue

        item_in_json = item.model_dump()

        mockProductsWithStock.append(
            {**item_in_json, "stock": products_list_stock[item.id]}
        )

        # Act
        cacheService.set_key(
            f"product:{item.id}",
            {**item_in_json, "stock": products_list_stock[item.id]},
        )

    # Assert
    mockProductsInCache: list[dict] = []

    for item in mockProductsWithStock:
        mockProductInCache = cacheService.get_key(
            f"product:{item['id']}",
            value_type="dict",
            deserialize=lambda data: TypeAdapter(
                ProductWithStock
            ).validate_python(data),
        )
        mockProductsInCache.append(mockProductInCache)

        assert mockProductInCache == item

    assert len(mockProductsInCache) == len(mockProductsWithStock)


def test_set_key_with_non_dict():
    # Arrange
    cacheService = CacheService()
    data = "um texto para dar erro"

    # Act
    cacheService.set_key("product:1", data)

    result = cacheService.get_key("product:1")

    # Assert
    assert type(result) is str
    assert result == data
