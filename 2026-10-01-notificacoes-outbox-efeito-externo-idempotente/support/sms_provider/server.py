"""Provedor de SMS fake — APOIO ao desafio, não faz parte dele.

Simula um provedor externo com falhas controláveis. Não tem nenhuma lógica
de outbox, retry, idempotência do lado do cliente ou reconciliação: isso é
o que o desafio pede para você construir.

Endpoints:
    POST /messages        {to, template, body, client_reference}
                          header opcional Idempotency-Key
                          → 202 {"provider_message_id": "..."}
    GET  /messages?client_reference=...   → lista do que foi aceito
    GET  /admin/config    → configuração atual
    POST /admin/config    {"FAIL_RATE": 50, ...}  → muda em tempo real
    POST /admin/reset     → apaga mensagens aceitas e chaves (não o log)
    GET  /health

Comportamento (variáveis de ambiente, ou /admin/config):
    FAIL_RATE            % de 500 SEM aceitar a mensagem
    AMBIGUOUS_RATE       % em que a mensagem É aceita e entregue, mas a
                         conexão é fechada sem resposta (cliente vê erro
                         de conexão ou timeout)
    RATE_LIMIT           requisições/s antes de 429 + Retry-After (0 = off)
    LATENCY_MS           latência artificial antes de responder
    IDEMPOTENCY_SUPPORT  on | off
    DELIVERED_LOG        caminho do log append-only (delivered.jsonl)

Cada SMS "entregue" vira uma linha em DELIVERED_LOG. É a prova usada nos
critérios de aceite: client_reference repetido ali = SMS duplicado.
"""

import json
import os
import random
import threading
import time
import uuid
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

REQUIRED_FIELDS = ("to", "template", "body", "client_reference")


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


config = {
    "FAIL_RATE": _env_float("FAIL_RATE", 0),
    "AMBIGUOUS_RATE": _env_float("AMBIGUOUS_RATE", 0),
    "RATE_LIMIT": _env_float("RATE_LIMIT", 0),
    "LATENCY_MS": _env_float("LATENCY_MS", 0),
    "IDEMPOTENCY_SUPPORT": os.getenv("IDEMPOTENCY_SUPPORT", "on"),
}
DELIVERED_LOG = os.getenv("DELIVERED_LOG", "/data/delivered.jsonl")

lock = threading.Lock()
accepted: list[dict] = []  # mensagens aceitas (para reconciliação)
idempotency: dict[str, dict] = {}  # chave → resposta já devolvida
window = {"second": 0, "count": 0}  # janela do rate limit


def _deliver(payload: dict, key: str | None) -> dict:
    """Aceita e "entrega" a mensagem. Chamado com o lock adquirido."""
    record = {
        "provider_message_id": str(uuid.uuid4()),
        "to": payload["to"],
        "template": payload["template"],
        "client_reference": payload["client_reference"],
        "idempotency_key": key,
        "accepted_at": datetime.now(UTC).isoformat(),
    }
    accepted.append(record)
    with open(DELIVERED_LOG, "a", encoding="utf-8") as log:
        log.write(json.dumps(record) + "\n")
    return {"provider_message_id": record["provider_message_id"]}


def _rate_limited() -> bool:
    limit = config["RATE_LIMIT"]
    if limit <= 0:
        return False
    now = int(time.time())
    with lock:
        if window["second"] != now:
            window["second"], window["count"] = now, 0
        window["count"] += 1
        return window["count"] > limit


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # log curto em stdout
        print(f"{self.command} {self.path} {fmt % args}", flush=True)

    # --- utilitários -----------------------------------------------------

    def _send(self, status: int, body: dict | list, headers=None) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(length) or b"null")
        except json.JSONDecodeError:
            return None

    def _drop_connection(self) -> None:
        """Fecha o socket sem escrever nenhuma resposta."""
        self.close_connection = True
        self.connection.close()

    # --- rotas -----------------------------------------------------------

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/health":
            return self._send(200, {"status": "ok"})
        if url.path == "/admin/config":
            return self._send(200, config)
        if url.path == "/messages":
            ref = parse_qs(url.query).get("client_reference", [None])[0]
            with lock:
                found = [m for m in accepted if m["client_reference"] == ref]
            return self._send(200, found)
        return self._send(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        url = urlparse(self.path)
        if url.path == "/messages":
            return self._post_message()
        if url.path == "/admin/config":
            changes = self._read_json() or {}
            unknown = set(changes) - set(config)
            if unknown:
                return self._send(400, {"error": f"unknown: {unknown}"})
            config.update(changes)
            return self._send(200, config)
        if url.path == "/admin/reset":
            with lock:
                accepted.clear()
                idempotency.clear()
            return self._send(200, {"status": "reset"})
        return self._send(404, {"error": "NOT_FOUND"})

    def _post_message(self):
        payload = self._read_json()
        if not isinstance(payload, dict) or any(
            not payload.get(field) for field in REQUIRED_FIELDS
        ):
            return self._send(400, {"error": "INVALID_REQUEST"})

        if _rate_limited():
            return self._send(
                429, {"error": "RATE_LIMITED"}, {"Retry-After": "1"}
            )

        if config["LATENCY_MS"] > 0:
            time.sleep(config["LATENCY_MS"] / 1000)

        key = self.headers.get("Idempotency-Key")
        use_key = key and config["IDEMPOTENCY_SUPPORT"] == "on"
        with lock:
            if use_key and key in idempotency:
                return self._send(202, idempotency[key])

        roll = random.uniform(0, 100)
        if roll < config["FAIL_RATE"]:
            return self._send(500, {"error": "PROVIDER_ERROR"})

        with lock:
            response = _deliver(payload, key)
            if use_key:
                idempotency[key] = response

        if roll < config["FAIL_RATE"] + config["AMBIGUOUS_RATE"]:
            return self._drop_connection()  # aceitou, mas não responde
        return self._send(202, response)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(DELIVERED_LOG) or ".", exist_ok=True)
    port = int(os.getenv("PORT", "9000"))
    print(f"fake SMS provider on :{port} config={config}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
