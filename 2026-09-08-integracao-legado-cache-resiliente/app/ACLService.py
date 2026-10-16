import json
import random
import time

import httpx
from pydantic import BaseModel, TypeAdapter

from .CacheService import CacheService

PRODUCT_PREFIX_KEY = "product"


class ProductWithStock(BaseModel):
    id: str
    name: str
    category: str
    base_price: float
    stock: int


class Product(BaseModel):
    id: str
    name: str
    category: str
    base_price: float


class ProductStock(BaseModel):
    available_stock: int
    product_id: str


class ACLService:
    products: list[Product]
    http_client: httpx.AsyncClient
    cacheService: CacheService
    base_url: str = "http://127.0.0.1:9000"

    def __init__(self, fail_rate=0.75, min_delay=3.0, max_delay=5.0):
        self.cacheService = CacheService()
        self.http_client = httpx.AsyncClient(base_url=self.base_url)
        self.products: list[Product] = self.get_products()
        self.set_fail_rate(
            fail_rate=fail_rate, min_delay=min_delay, max_delay=max_delay
        )

    def set_fail_rate(self, fail_rate, min_delay, max_delay):
        httpx.post(
            f"{self.base_url}/admin/config",
            params={
                "failure_rate": fail_rate,
                "min_delay_seconds": min_delay,
                "max_delay_seconds": max_delay,
            },
        )

    def get_products(self) -> list[Product]:
        with open("data/products.json", "r", encoding="utf8") as file:
            return TypeAdapter(list[Product]).validate_python(json.load(file))

    async def list_products(self) -> list[ProductWithStock]:
        products = await self.backoff(5)

        return self.adapter(products)

    def adapter(self, legacy_products):
        return TypeAdapter(list[ProductWithStock]).validate_python(
            legacy_products
        )

    async def backoff(self, max_attempts=2, delay=1) -> list[dict]:
        x = 0

        while x < max_attempts:
            try:
                products_with_stock: list[dict] = []

                for item in self.products:
                    has_item: ProductWithStock = self.cacheService.get_key(
                        key=f"{PRODUCT_PREFIX_KEY}:{item.id}",
                        value_type="dict",
                        deserialize=lambda data: TypeAdapter(
                            ProductWithStock
                        ).validate_python(data),
                    )

                    if has_item:
                        products_with_stock.append(has_item.model_dump())
                        continue

                    response = await self.http_client.get(f"stock/{item.id}")

                    if response.status_code == 404:
                        continue

                    if response.status_code == 200:
                        product_stock: ProductStock = TypeAdapter(
                            ProductStock
                        ).validate_python(response.json())

                        payload: dict = {
                            **item.model_dump(),
                            "stock": product_stock.available_stock,
                        }

                        products_with_stock.append(payload)

                        self.cacheService.set_key(
                            key=f"{PRODUCT_PREFIX_KEY}:{item.id}",
                            value=payload,
                        )

                    response.raise_for_status()

                return products_with_stock
            except httpx.HTTPStatusError as e:
                x += 1
                print(f"Fail to connect to server, retry {x}")

                if x == max_attempts:
                    raise ConnectionError("Legacy connection failed!", e)

                sleep_time = random.uniform(0, delay * (2**x))
                time.sleep(sleep_time)

    async def health_check(self):
        try:
            response = await self.http_client.get("stock/ID")
            response.raise_for_status()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 500:
                raise ConnectionError("Legacy connection failed!", e)
            return True
