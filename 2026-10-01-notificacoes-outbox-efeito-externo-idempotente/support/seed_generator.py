"""Gera o dataset do pré-requisito — APOIO ao desafio, não faz parte dele.

    python3 support/seed_generator.py      # reescreve seed/

Determinístico (semente fixa): rodar de novo produz os mesmos arquivos.
Só gera dados e o roteiro de transições. Não calcula nenhuma notificação
esperada: decidir o que cada evento gera é a regra de negócio, e é sua.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
DAY = datetime.fromisoformat("2026-10-05T00:00:00-03:00")  # segunda
DDDS = ["11", "21", "31", "41", "51", "61", "71", "81"]
CATALOG = [
    ("SKU-CAP", "Boné", 4500),
    ("SKU-TEE", "Camiseta", 7990),
    ("SKU-MUG", "Caneca", 3290),
    ("SKU-BAG", "Mochila", 18900),
    ("SKU-SOCK", "Meia", 1990),
    ("SKU-BOTTLE", "Garrafa", 5990),
]

rng = random.Random(42)
customers: list[dict] = []
orders: list[dict] = []
script: list[dict] = []


def at(day: int, hhmm: str, ms: int = 0) -> datetime:
    hour, minute = map(int, hhmm.split(":"))
    return DAY + timedelta(
        days=day, hours=hour, minutes=minute, milliseconds=ms
    )


def valid_phone() -> str:
    return f"+55{rng.choice(DDDS)}9{rng.randrange(10**7, 10**8)}"


def add_customer(phone=None, opt_in=True, note=None) -> str:
    key = f"C{len(customers) + 1:02d}"
    customers.append(
        {
            "key": key,
            "name": f"Customer {key}",
            "phone": phone or valid_phone(),
            "sms_opt_in": opt_in,
            **({"note": note} if note else {}),
        }
    )
    return key


def add_order(customer, items=None, recipient_phone=None, note=None) -> str:
    key = f"O{len(orders) + 1:02d}"
    if items is None:
        picked = rng.sample(CATALOG, rng.randint(1, 3))
        items = [(sku, name, price, rng.randint(1, 2)) for sku, name, price
                 in picked]
    lines = [
        {"sku": sku, "name": name, "unit_price_cents": price, "quantity": qty}
        for sku, name, price, qty in items
    ]
    orders.append(
        {
            "key": key,
            "customer": customer,
            "items": lines,
            "total_cents": sum(
                line["unit_price_cents"] * line["quantity"] for line in lines
            ),
            "recipient_phone": recipient_phone,
            **({"note": note} if note else {}),
        }
    )
    return key


class Flow:
    """Monta o roteiro de um pedido, controlando o expected_version."""

    def __init__(self, order: str, created: datetime, note=None) -> None:
        self.order, self.version = order, 1
        step = {"at": created, "action": "create_order", "order": order}
        script.append({**step, **({"note": note} if note else {})})

    def go(self, when, to, note=None, ok=True, **extra) -> "Flow":
        script.append(
            {
                "at": when,
                "action": "transition",
                "order": self.order,
                "to": to,
                "expected_version": self.version,
                **extra,
                **({"note": note} if note else {}),
            }
        )
        if ok:
            self.version += 1
        return self


def tracking() -> str:
    return f"BR{rng.randrange(10**8, 10**9)}"


def single_item(price: int):
    return [("SKU-GIFT", "Vale-presente", price, 1)]


# --- casos propositais (lista "Dataset" do README) ----------------------

c = add_customer("+551187654321", note="telefone inválido: sem o 9 inicial")
Flow(add_order(c), at(0, "09:00")).go(at(0, "09:05"), "PAID")

c = add_customer("+55198765432", note="telefone inválido: DDD de 1 dígito")
Flow(add_order(c, single_item(9000)), at(0, "09:10")).go(
    at(0, "09:40"), "ABANDONED"
)

c = add_customer(opt_in=False, note="opt-out com pedido abandonado")
Flow(add_order(c, single_item(12000)), at(0, "10:00")).go(
    at(0, "10:30"), "ABANDONED"
)
c = add_customer(opt_in=False, note="opt-out com pedido pago")
Flow(add_order(c), at(0, "10:05")).go(at(0, "10:10"), "PAID")
c = add_customer(opt_in=False, note="opt-out com pedido enviado")
Flow(add_order(c), at(0, "10:15")).go(at(0, "10:20"), "PAID").go(
    at(0, "15:00"), "SHIPPED", tracking_code=tracking()
)

shared = valid_phone()
c1 = add_customer(shared, note="divide o telefone com o próximo cliente")
c2 = add_customer(shared, note="divide o telefone com o cliente anterior")
Flow(add_order(c1, single_item(8000)), at(0, "09:30")).go(
    at(0, "10:00"), "ABANDONED", note="1º abandono do telefone compartilhado"
)
Flow(add_order(c2, single_item(8000)), at(0, "12:30")).go(
    at(0, "13:00"), "ABANDONED",
    note="2º abandono do mesmo telefone, 3 h depois",
)

c = add_customer(note="abandona às 22:30 e paga às 07:40")
Flow(add_order(c, single_item(15000)), at(0, "22:00")).go(
    at(0, "22:30"), "ABANDONED"
).go(at(1, "07:40"), "PAID")

c = add_customer(note="troca de telefone às 23:00, depois do abandono")
Flow(add_order(c, single_item(11000)), at(0, "22:10")).go(
    at(0, "22:30"), "ABANDONED"
)
script.append(
    {
        "at": at(0, "23:00"),
        "action": "update_customer",
        "customer": c,
        "phone": valid_phone(),
        "note": "troca de telefone antes do envio agendado das 08:00",
    }
)

c = add_customer(note="pago e estornado em menos de 1 s")
Flow(add_order(c), at(0, "14:00")).go(at(0, "14:05"), "PAID").go(
    at(0, "14:05", ms=400), "REFUNDED"
)

c = add_customer(note="carrinho de exatamente R$ 50,00")
Flow(add_order(c, single_item(5000)), at(0, "11:00")).go(
    at(0, "11:30"), "ABANDONED"
)
c = add_customer(note="carrinho de R$ 49,99")
Flow(add_order(c, single_item(4999)), at(0, "11:05")).go(
    at(0, "11:35"), "ABANDONED"
)

c = add_customer(note="tenta enviar sem tracking_code")
Flow(add_order(c), at(0, "08:30")).go(at(0, "08:35"), "PAID").go(
    at(0, "16:00"), "SHIPPED", ok=False,
    note="sem tracking_code: deve falhar com 422",
).go(at(0, "16:10"), "SHIPPED", tracking_code=tracking())

c = add_customer(note="pedido com recebedor diferente")
Flow(add_order(c, recipient_phone=valid_phone()), at(0, "09:15")).go(
    at(0, "09:20"), "PAID"
).go(at(0, "17:00"), "SHIPPED", tracking_code=tracking())
c = add_customer(note="pedido com recebedor igual ao comprador")
Flow(add_order(c, recipient_phone=customers[-1]["phone"]), at(0, "09:25")).go(
    at(0, "09:30"), "PAID"
).go(at(0, "17:05"), "SHIPPED", tracking_code=tracking())
c = add_customer(note="pedido com recebedor de telefone inválido")
Flow(add_order(c, recipient_phone="+5521912345"), at(0, "09:35")).go(
    at(0, "09:40"), "PAID"
).go(at(0, "17:10"), "SHIPPED", tracking_code=tracking())

c = add_customer(note="duas transições simultâneas no pedido CREATED")
flow = Flow(add_order(c), at(0, "12:00"))
flow.go(at(0, "12:10"), "PAID", ok=False, concurrent="G1",
        note="simultânea com ABANDONED: só uma vence")
flow.go(at(0, "12:10"), "ABANDONED", ok=False, concurrent="G1",
        note="simultânea com PAID: só uma vence")

# --- pedidos comuns até completar 60 ------------------------------------

regular = [add_customer() for _ in range(30 - len(customers))]
abandoned_today: set[str] = set()
kinds = ["delivered", "refunded_after_ship", "paid_only", "created_only",
         "abandoned_then_paid", "abandoned"]
while len(orders) < 60:
    customer = rng.choice(regular)
    kind = rng.choice(kinds)
    if kind.startswith("abandoned"):
        if customer in abandoned_today:
            kind = "paid_only"  # evita teto de frequência acidental
        else:
            abandoned_today.add(customer)
    hour, minute = rng.randint(8, 18), rng.choice([0, 15, 30, 45])
    start = at(0, f"{hour:02d}:{minute:02d}")
    flow = Flow(add_order(customer), start)
    if kind == "created_only":
        continue
    if kind.startswith("abandoned"):
        flow.go(start + timedelta(minutes=30), "ABANDONED")
        if kind == "abandoned_then_paid":
            flow.go(start + timedelta(minutes=50), "PAID")
        continue
    flow.go(start + timedelta(minutes=5), "PAID")
    if kind == "paid_only":
        continue
    flow.go(start + timedelta(hours=4), "SHIPPED", tracking_code=tracking())
    flow.go(
        start + timedelta(days=1),
        "DELIVERED" if kind == "delivered" else "REFUNDED",
    )

# --- saída ---------------------------------------------------------------

SEED_DIR.mkdir(exist_ok=True)
(SEED_DIR / "customers.json").write_text(
    json.dumps(customers, indent=2, ensure_ascii=False) + "\n"
)
(SEED_DIR / "orders.json").write_text(
    json.dumps(orders, indent=2, ensure_ascii=False) + "\n"
)
script.sort(key=lambda step: step["at"])  # sort estável: G1 fica junto
with open(SEED_DIR / "transitions.jsonl", "w", encoding="utf-8") as out:
    for step in script:
        step = {**step, "at": step["at"].isoformat(timespec="milliseconds")}
        out.write(json.dumps(step, ensure_ascii=False) + "\n")
print(f"{len(customers)} clientes, {len(orders)} pedidos, "
      f"{len(script)} passos em {SEED_DIR}")
