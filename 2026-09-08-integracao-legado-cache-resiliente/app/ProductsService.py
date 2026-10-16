from enum import IntEnum

from .ACLService import ACLService, Product

aclService = ACLService()

""" Objetivo:

Expor um catálogo de produtos e visualizar detalhes de um produto esepecífico

Regras:

preço final = preço base * (1 - desconto) * (1 + imposto)
impostos = Eletronicos 12%, Livros 4%, Comida 7%, Roupas 8%
desconto = 10% se estoque disponível > 500 unidades,
    5% se estoque disponível > 100,
    e 0% se for menor que 100 unidades

    > - `category_tax`: `ELECTRONICS` 12%, `BOOKS` 4%, `FOOD` 7%, `CLOTHING` 8%.
> - `stock_discount`: 10% se estoque disponível > 500 unidades, 5% se > 100, 0% caso contrário. **O estoque disponível vem do 

"""


class CategoryTax(IntEnum):
    """Percentagem como um inteiro"""

    ELECTRONICS = 12
    BOOKS = 4
    FOOD = 7
    CLOTHING = 8


async def get_products():
    products: list[Product] = await aclService.list_products()

    for item in products:
        item.price = _define_price(item)

    return products


def _define_price(product: Product) -> float:
    return (
        product.base_price
        + _define_category_tax(product)
        + _define_discount_stock(product)
    )


def _define_category_tax(product: Product) -> float:
    tax = CategoryTax(product.category) / 100

    return float(product.base_price * tax)


def _define_discount_stock(product: Product) -> float:
    stock_discount = 0

    if product.stock > 500:
        stock_discount = 10
    elif product.stock > 100 and product.stock < 500:
        stock_discount = 5

    discount = stock_discount / 100

    return product.base_price * discount
