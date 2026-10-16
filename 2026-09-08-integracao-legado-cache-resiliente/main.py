from fastapi import Depends, FastAPI

from app.ProductsService import get_products

app = FastAPI(dependencies=[Depends(get_products)])


@app.get("/products")
def list_products():
    return {"message": get_products()}


@app.get("/products/{product_id}")
def show_product(product_id: str):
    return {"message": product_id}
