from fastapi import FastAPI

app = FastAPI()
""" Tarefas:

Expor um catálogo de produtos e visualizar detalhes de um produto esepecífico

Regras:

preço final = preço base * (1 - desconto) * (1 + imposto)
impostos = Eletronicos 12%, Livros 4%, Comida 7%, Roupas 8%
desconto = 10% se estoque disponível > 500 unidades,
    5% se estoque disponível > 100,
    e 0% se for menor que 100 unidades
"""


@app.get("/")
async def hello_world():
    return {"message": "Hello"}
