"""Fake do sistema legado de estoque — apoio ao desafio, não faz parte dele.

Simula, via HTTP, o comportamento de um sistema externo lento e instável
(latência artificial + falha aleatória configurável). Não implementa nenhum
padrão de resiliência — isso é o que o desafio pede para você construir do
lado de fora, na sua API.

Rodar em processo separado da API principal, ex.:
    uv run fastapi dev legacy_service.py --port 9000
"""

import asyncio
import json
import os
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Legacy Stock Service (fake)")

_STOCK: dict[str, int] = json.loads(
    (Path(__file__).parent / "data" / "legacy_stock.json").read_text()
)

_config = {
    "failure_rate": float(os.getenv("LEGACY_FAILURE_RATE", "0.2")),
    "min_delay_seconds": float(os.getenv("LEGACY_MIN_DELAY", "3.0")),
    "max_delay_seconds": float(os.getenv("LEGACY_MAX_DELAY", "5.0")),
}


@app.get("/stock/{product_id}")
async def get_stock(product_id: str):
    await asyncio.sleep(random.uniform(_config["min_delay_seconds"], _config["max_delay_seconds"]))

    if random.random() < _config["failure_rate"]:
        raise HTTPException(status_code=503, detail="legacy system unavailable")

    if product_id not in _STOCK:
        raise HTTPException(status_code=404, detail="product not found in legacy system")

    return {"product_id": product_id, "available_stock": _STOCK[product_id]}


@app.get("/admin/config")
async def get_config():
    return _config


@app.post("/admin/config")
async def set_config(
    failure_rate: float | None = None,
    min_delay_seconds: float | None = None,
    max_delay_seconds: float | None = None,
):
    """Ajusta o comportamento em runtime — útil para forçar falha em 100%
    num teste sem reiniciar o processo (ver critérios de aceite do README)."""
    if failure_rate is not None:
        _config["failure_rate"] = failure_rate
    if min_delay_seconds is not None:
        _config["min_delay_seconds"] = min_delay_seconds
    if max_delay_seconds is not None:
        _config["max_delay_seconds"] = max_delay_seconds
    return _config


@app.post("/admin/stock/{product_id}")
async def set_stock(product_id: str, available_stock: int):
    """Atualiza o estoque de um produto — use para disparar, do lado do
    legado, a mudança de dado que sua camada de invalidação ativa precisa
    detectar e refletir sem esperar o TTL."""
    _STOCK[product_id] = available_stock
    return {"product_id": product_id, "available_stock": available_stock}
