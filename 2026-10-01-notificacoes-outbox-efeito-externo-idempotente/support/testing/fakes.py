"""Dublês de teste — APOIO ao desafio.

Não decidem nada: só registram o que o seu código fez, para os testes
conferirem. Imitam a interface do aio-pika; se você usar outra biblioteca,
adapte os nomes dos métodos.

    from support.testing.fakes import FakeIncomingMessage, FakeBroker, x_death

    message = FakeIncomingMessage({"event_id": "..."}, headers=x_death(2))
    await seu_consumidor(message)
    assert message.acked
"""

import asyncio
import json
from typing import Any


def x_death(
    count: int,
    queue: str = "notifications.events",
    reason: str = "rejected",
) -> dict[str, Any]:
    """Header x-death como o RabbitMQ monta depois de `count` dead-letters
    de `queue` pelo motivo `reason`. Ajuste o nome da fila ao seu."""
    return {"x-death": [{"queue": queue, "reason": reason, "count": count}]}


class FakeIncomingMessage:
    """Mensagem recebida: registra ack, nack e reject (com ou sem requeue)."""

    def __init__(
        self,
        body: dict[str, Any] | bytes,
        *,
        message_id: str | None = None,
        correlation_id: str | None = None,
        headers: dict[str, Any] | None = None,
        redelivered: bool = False,
    ) -> None:
        self.body = body if isinstance(body, bytes) else json.dumps(
            body
        ).encode("utf-8")
        self.message_id = message_id
        self.correlation_id = correlation_id
        self.headers = headers or {}
        self.redelivered = redelivered
        self.acked = False
        self.nacked = False
        self.rejected = False
        self.requeue: bool | None = None

    @property
    def settled(self) -> bool:
        """True se o consumidor respondeu ao broker de alguma forma."""
        return self.acked or self.nacked or self.rejected

    async def ack(self, multiple: bool = False) -> None:
        self.acked = True

    async def nack(self, multiple: bool = False, requeue: bool = True):
        self.nacked, self.requeue = True, requeue

    async def reject(self, requeue: bool = False) -> None:
        self.rejected, self.requeue = True, requeue


class FakeBroker:
    """Publicação: registra o que foi publicado e falha sob comando.

    fail_next = N   → as próximas N publicações levantam fail_with
    delay = 0.2     → cada publicação espera 0,2 s (para provocar corrida)
    """

    def __init__(self, fail_with: type[Exception] = ConnectionError) -> None:
        self.published: list[dict[str, Any]] = []
        self.fail_next = 0
        self.fail_with = fail_with
        self.delay = 0.0

    async def publish(
        self,
        routing_key: str,
        body: dict[str, Any],
        headers: dict[str, Any] | None = None,
        **properties: Any,
    ) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail_next > 0:
            self.fail_next -= 1
            raise self.fail_with("simulated broker failure")
        self.published.append(
            {
                "routing_key": routing_key,
                "body": body,
                "headers": headers or {},
                **properties,
            }
        )

    def to(self, routing_key: str) -> list[dict[str, Any]]:
        """Só o que foi publicado numa fila ou routing key."""
        return [p for p in self.published if p["routing_key"] == routing_key]
