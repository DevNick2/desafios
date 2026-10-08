# Peças de apoio

Tudo nesta pasta (`support/`), mais `seed/` e `docker-compose.yml`, é
**apoio**: dado, infraestrutura e dublês que existem só para o seu código
ter com o que conversar. Nada aqui decide o que o desafio pede para você
aprender a decidir.

| Peça | O que é | O que **não** faz |
|---|---|---|
| `docker-compose.yml` | Postgres, RabbitMQ (painel em `:15672`), provedor fake (`:9000`), Jaeger (`:16686`), Prometheus (`:9090`) | Não declara filas nem exchanges: a topologia é sua |
| `sms_provider/` | Provedor de SMS fake com `FAIL_RATE`, `AMBIGUOUS_RATE`, `RATE_LIMIT`, `LATENCY_MS` e `IDEMPOTENCY_SUPPORT`; grava cada SMS entregue em `sms_provider/data/delivered.jsonl` | Não tem retry, outbox, nem reconciliação do lado do cliente |
| `seed_generator.py` | Gera `seed/` (30 clientes, 60 pedidos, roteiro de 170 passos) de forma determinística | Não calcula quais notificações cada evento gera |
| `replay.py` | Aplica `seed/transitions.jsonl` na sua API, com o horário simulado no header `X-Simulated-Now` e os passos `concurrent` disparados juntos | Não confere se a resposta está certa: só mostra o HTTP |
| `testing/fakes.py` | `FakeIncomingMessage` (registra ack/nack/reject), `FakeBroker` (registra publicações, falha sob comando) e `x_death(n)` | Não simula retry nem dead-letter: isso é o seu código + o RabbitMQ real |
| `prometheus.yml` | Alvos de scrape para os seus serviços (`:8000` a `:8003`) | Ajuste as portas ao que você usar |

Núcleo, e portanto seu: a API, a máquina de estados do pedido e da
notificação, a regra de notificação, a outbox e o relay, a topologia do
RabbitMQ, o consumidor, o reconciliador, o tracing, os testes e os
documentos.

## Comandos

```bash
docker compose up -d --build                  # infraestrutura
python3 support/replay.py --api http://127.0.0.1:8000
python3 support/seed_generator.py             # regera seed/ (mesmos dados)

# provedor fake em tempo real, sem reiniciar:
curl -X POST localhost:9000/admin/config -d '{"FAIL_RATE": 20, "AMBIGUOUS_RATE": 5}'
curl -X POST localhost:9000/admin/reset       # limpa aceitas e chaves
curl 'localhost:9000/messages?client_reference=<id>'

# caos:
docker compose stop rabbitmq; sleep 60; docker compose start rabbitmq
kill -STOP <pid do consumidor>; ...; kill -CONT <pid>

# prova de duplicata: client_reference repetido no log
jq -r .client_reference support/sms_provider/data/delivered.jsonl \
  | sort | uniq -d
```

## Contrato que o replayer assume

Os endpoints de pedido estão no README. Para carregar o seed, a sua API
também precisa de:

- `POST /customers` com `{name, phone, sms_opt_in}` → `{"id": ...}`
- `PATCH /customers/{id}` com `{phone}`
- `POST /orders` com `{customer_id, items, total_cents, recipient_phone}`
  → `{"id": ...}`; a versão inicial do pedido é `1`

Se o seu contrato for diferente, ajuste `replay.py`: ele é apoio.

## Formato do roteiro (`seed/transitions.jsonl`)

Uma ação por linha, em ordem de horário:

```json
{"at": "...-03:00", "action": "create_order", "order": "O01"}
{"at": "...", "action": "transition", "order": "O01", "to": "PAID", "expected_version": 1}
{"at": "...", "action": "transition", "order": "O13", "to": "SHIPPED", "expected_version": 2, "tracking_code": "BR..."}
{"at": "...", "action": "update_customer", "customer": "C09", "phone": "+55..."}
{"at": "...", "action": "transition", "order": "O17", "to": "PAID", "expected_version": 1, "concurrent": "G1"}
```

O campo `note` marca os casos propositais da lista "Dataset" do README.
`expected_version` assume que você não implementou nada errado antes: se
uma transição anterior falhar onde não devia, as seguintes vão falhar com
`VERSION_CONFLICT` em cascata, o que também é um bom sinal de diagnóstico.
