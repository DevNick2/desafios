"""Aplica seed/transitions.jsonl na sua API — APOIO ao desafio.

    python3 support/replay.py --api http://127.0.0.1:8000

Só biblioteca padrão. Não decide nada: envia cada passo do roteiro, na
ordem, e mostra o HTTP que a sua API respondeu. Passos com o mesmo campo
"concurrent" são disparados ao mesmo tempo (threads + barreira).

Contrato que o replayer assume da sua API (ajuste aqui se o seu for
diferente):

    POST  /customers                 {name, phone, sms_opt_in} → {"id": ...}
    PATCH /customers/{id}            {phone}
    POST  /orders                    {customer_id, items, total_cents,
                                      recipient_phone} → {"id": ...}
    POST  /orders/{id}/transitions   {to, expected_version[, tracking_code]}

Toda requisição leva o horário simulado do passo no header
X-Simulated-Now (mude com --clock-header), para o seu relógio injetável.
Os ids devolvidos pela API ficam em replay_ids.json.
"""

import argparse
import json
import threading
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--clock-header", default="X-Simulated-Now")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--ids-file", default="replay_ids.json")
    return parser.parse_args()


class Client:
    def __init__(self, args: argparse.Namespace) -> None:
        self.api = args.api.rstrip("/")
        self.clock_header = args.clock_header
        self.timeout = args.timeout

    def call(self, method, path, body, now) -> tuple[int, dict]:
        request = urllib.request.Request(
            self.api + path,
            data=json.dumps(body).encode(),
            method=method,
            headers={
                "Content-Type": "application/json",
                self.clock_header: now,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as r:
                status, raw = r.status, r.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        try:
            return status, json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return status, {"raw": raw.decode(errors="replace")}


def main() -> int:
    args = parse_args()
    client = Client(args)
    customers = {
        c["key"]: c
        for c in json.loads((SEED_DIR / "customers.json").read_text())
    }
    orders = {
        o["key"]: o for o in json.loads((SEED_DIR / "orders.json").read_text())
    }
    steps = [
        json.loads(line)
        for line in (SEED_DIR / "transitions.jsonl").read_text().splitlines()
    ]
    ids: dict[str, object] = {}
    results: Counter = Counter()

    def report(step, status, body):
        label = step.get("to") or step["action"]
        results[(step["action"], status)] += 1
        note = f"  # {step['note']}" if step.get("note") else ""
        error = f" {body.get('error') or body.get('detail') or ''}"
        if status < 400:
            error = ""
        print(f"{step['at']} {step.get('order') or step.get('customer'):>4}"
              f" {label:<14} → {status}{error}{note}")

    # Clientes primeiro, no horário do primeiro passo.
    first_at = steps[0]["at"]
    for key, customer in customers.items():
        status, body = client.call(
            "POST",
            "/customers",
            {k: customer[k] for k in ("name", "phone", "sms_opt_in")},
            first_at,
        )
        if status >= 400 or "id" not in body:
            print(f"falha ao criar {key}: {status} {body}")
            return 1
        ids[key] = body["id"]

    def run(step):
        if step["action"] == "create_order":
            order = orders[step["order"]]
            status, body = client.call(
                "POST",
                "/orders",
                {
                    "customer_id": ids[order["customer"]],
                    "items": order["items"],
                    "total_cents": order["total_cents"],
                    "recipient_phone": order["recipient_phone"],
                },
                step["at"],
            )
            if "id" in body:
                ids[step["order"]] = body["id"]
        elif step["action"] == "update_customer":
            status, body = client.call(
                "PATCH",
                f"/customers/{ids[step['customer']]}",
                {"phone": step["phone"]},
                step["at"],
            )
        else:
            payload = {"to": step["to"],
                       "expected_version": step["expected_version"]}
            if "tracking_code" in step:
                payload["tracking_code"] = step["tracking_code"]
            status, body = client.call(
                "POST",
                f"/orders/{ids[step['order']]}/transitions",
                payload,
                step["at"],
            )
        report(step, status, body)

    index = 0
    while index < len(steps):
        group = steps[index].get("concurrent")
        if not group:
            run(steps[index])
            index += 1
            continue
        batch = [s for s in steps[index:] if s.get("concurrent") == group]
        barrier = threading.Barrier(len(batch))

        def fire(step):
            barrier.wait()
            run(step)

        threads = [threading.Thread(target=fire, args=(s,)) for s in batch]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        index += len(batch)

    Path(args.ids_file).write_text(json.dumps(ids, indent=2) + "\n")
    print("\nResumo (ação, HTTP): quantidade")
    for (action, status), count in sorted(results.items()):
        print(f"  {action:<16} {status}: {count}")
    print(f"ids da API em {args.ids_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
