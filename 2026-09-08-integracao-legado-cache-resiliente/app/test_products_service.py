from . import ProductsService


async def test_list_products_with_price_successfuly(monkeypatch):
    # Arrange
    # async def mock_list_products():
    #     return ""

    # monkeypatch.setattr(ACLService, "list_products", mock_list_products)

    # Act
    products = await ProductsService.get_products()

    breakpoint()
    # Assert
