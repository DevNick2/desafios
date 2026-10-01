# Desafio — Notificações por Eventos sem Perda e sem Duplicata (Outbox, Escrita Condicional e Efeito Externo Idempotente)

> Nível: **Avançado** (pl↔sr)
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito, não só o desafio em si.

---

## Motivação

Todo sistema que reage a eventos de negócio com uma **ação no mundo real** (mandar SMS, cobrar um cartão, emitir uma nota) tem o mesmo par de exigências: **nenhum evento pode se perder** e **nenhuma ação pode acontecer duas vezes**. Mensageria só garante entrega *pelo menos uma vez*, então as duas exigências precisam ser construídas pela aplicação.

Saber os nomes das peças (DLQ, chave de idempotência, checagem de status) não basta. O que separa um desenho correto de um que parece correto é conhecer **como cada peça falha**:

- deduplicação por **janela de tempo** parece idempotência, mas deixa passar o retry tardio e engole eventos legítimos próximos;
- "ler o status e depois processar" tem **condição de corrida** entre consumidores;
- gravar no banco e publicar na fila são **duas escritas**, e a segunda pode falhar depois do commit da primeira;
- o efeito externo tem um caso que nenhuma fila resolve: o provedor **aceitou** a mensagem, mas a resposta nunca chegou.

Este desafio exercita esses quatro modos de falha **provocando-os de propósito** e medindo o resultado. Também cobre duas lacunas práticas: **tracing distribuído** com OpenTelemetry e o hábito de **ter números medidos** (vazão e latência) do sistema que você opera.

É complementar ao desafio de webhook com parceiro (`2026-09-16-webhook-parceiro-delivery-oauth-sqs`): aquele trata a **entrada** dos eventos. Este trata o **produtor** (outbox) e a **saída** (efeito externo).

## Pré-requisito

Construa, dentro desta pasta, um serviço em **Python 3.12 + FastAPI + PostgreSQL** (todo identificador de código em inglês) com duas partes: a **máquina de estados do pedido** e a **regra de notificação**. Implemente exatamente estas regras.

### 1. Máquina de estados do pedido

Endpoints:
- `POST /orders` cria o pedido em `CREATED`.
- `POST /orders/{id}/transitions` com `{"to": "<STATUS>"}` muda o status.

Transições válidas (qualquer outra → erro `409 INVALID_TRANSITION`):

| De | Para |
|---|---|
| `CREATED` | `PAID`, `ABANDONED` |
| `ABANDONED` | `PAID` (cliente voltou e pagou) |
| `PAID` | `SHIPPED`, `REFUNDED` |
| `SHIPPED` | `DELIVERED`, `REFUNDED` |

Toda transição bem-sucedida gera um evento `ORDER_<STATUS>` (ex.: `ORDER_PAID`) com `event_id` (UUID v4), `order_id`, `occurred_at` e `order_version` (inteiro que incrementa a cada transição).

`SHIPPED` exige `tracking_code` no corpo; sem ele → `422 TRACKING_CODE_REQUIRED`.

### 2. Regra de notificação (o que mandar para cada evento)

| Evento | Template | Tipo |
|---|---|---|
| `ORDER_PAID` | `PAYMENT_CONFIRMED` | transacional |
| `ORDER_SHIPPED` | `ORDER_SHIPPED` (inclui `tracking_code`) | transacional |
| `ORDER_REFUNDED` | `REFUND_ISSUED` | transacional |
| `ORDER_ABANDONED` | `CART_RECOVERY` | marketing |
| `ORDER_CREATED`, `ORDER_DELIVERED` | nenhuma mensagem | — |

Condições, avaliadas nesta ordem:

1. **Telefone inválido** (não é E.164 brasileiro: `+55`, DDD de 2 dígitos, celular de 9 dígitos começando com 9) → notificação `FAILED` com motivo `INVALID_PHONE`. **Nunca** é reenviada.
2. **Opt-out:** cliente com `sms_opt_in = false` recebe só **transacional**. Marketing → `SKIPPED` com motivo `OPTED_OUT`.
3. **Valor mínimo:** `CART_RECOVERY` só se o total do carrinho for **≥ R$ 50,00** (5000 centavos; R$ 49,99 não recebe) → senão `SKIPPED` / `BELOW_MINIMUM`.
4. **Teto de frequência:** no máximo **1** `CART_RECOVERY` por **telefone** a cada **24 h** (contando os já `SENT`) → senão `SKIPPED` / `FREQUENCY_CAP`.
5. **Horário de silêncio:** marketing não sai entre **21:00 e 08:00** (`America/Sao_Paulo`). Fica `SCHEDULED` para as 08:00 seguintes. Transacional sai a qualquer hora.
6. **Obsolescência:** se, no momento do envio, o pedido já avançou além do estado que gerou a notificação, ela vira `SKIPPED` / `STALE`. Exemplos: `CART_RECOVERY` agendado de um pedido que já foi pago; `ORDER_SHIPPED` de um pedido já `REFUNDED`.

> Os itens 4 e 5 são **regra de negócio**, não idempotência. O teto de frequência impede duas mensagens *diferentes* legítimas. A idempotência impede a *mesma* mensagem duas vezes. Essa distinção é cobrada nas decisões escritas (ver Requisito 10).

Endpoint de consulta: `GET /orders/{id}/notifications` lista as notificações do pedido com status e motivo.

### Dataset

Em `seed/`: **30 clientes** e **60 pedidos** (com itens e totais em centavos), contendo estes casos propositais:

- 2 clientes com telefone inválido (um sem o 9 inicial, um com DDD de 1 dígito);
- 3 clientes com `sms_opt_in = false`, um deles com pedido abandonado e outro com pedido pago;
- 1 carrinho abandonado de exatamente **R$ 50,00** e 1 de **R$ 49,99**;
- 2 pedidos abandonados do **mesmo telefone** com 3 h de intervalo (o segundo cai no teto de frequência);
- 1 pedido abandonado às **22:30** (agendado para 08:00) que é **pago às 07:40** (vira `STALE`);
- 1 pedido pago e estornado com **menos de 1 s** de intervalo (os dois eventos são legítimos e geram duas mensagens);
- 1 pedido `SHIPPED` sem `tracking_code` (deve falhar com `422`).

Junto, um roteiro `seed/transitions.jsonl` com a sequência de transições a aplicar e o horário simulado de cada uma. O serviço precisa aceitar um **relógio injetável** para os testes de horário.

A máquina de estados e a regra de notificação são **núcleo** e são suas.

## Ambiente de execução

Tudo roda com `docker compose`, sem conta em nenhuma nuvem:

| Dependência | Como roda |
|---|---|
| Fila SQS + DLQ (e SNS, se quiser fan-out) | **LocalStack** |
| Banco do serviço | PostgreSQL em container |
| Tracing | **Jaeger** (all-in-one) recebendo OTLP |
| Métricas | Prometheus em container (ou o endpoint `/metrics` lido direto) |
| **Provedor de SMS** | **Fake de apoio** (ver abaixo) |
| Conta / custo | Nenhum |

**O provedor de SMS fake** é peça de apoio (pode ser construída com ajuda, conforme a regra de núcleo vs. apoio). Expõe:

- `POST /messages` com `{to, template, body, client_reference}` → `202 {provider_message_id}`;
- header opcional `Idempotency-Key`: com o suporte **ligado**, a mesma chave devolve a mesma resposta sem enviar de novo; com ele **desligado**, o header é ignorado;
- `GET /messages?client_reference=...` → lista o que foi aceito com aquela referência (é a API de reconciliação).

Comportamento controlável por variável de ambiente:

- `FAIL_RATE`: percentual de `500` **sem** aceitar a mensagem;
- `AMBIGUOUS_RATE`: percentual em que o fake **aceita e "entrega" a mensagem**, mas fecha a conexão sem responder (o cliente vê timeout);
- `RATE_LIMIT`: requisições por segundo antes de devolver `429` com `Retry-After`;
- `LATENCY_MS`: latência artificial;
- `IDEMPOTENCY_SUPPORT`: `on` ou `off`.

Ele grava **cada SMS "entregue"** num log append-only (`delivered.jsonl`), que é a prova usada nos critérios de aceite.

A lógica que o desafio avalia (outbox, consumo, idempotência, máquina de estados da notificação, reconciliação, tracing) é **núcleo** e é sua.

## Contexto

Uma loja online notifica clientes por SMS a partir de eventos de pedido. A versão atual faz o `UPDATE` do pedido e, logo em seguida, publica o evento na fila, e o consumidor deduplica por `order_id` + horário. Três reclamações chegaram na mesma semana:

- clientes receberam **duas confirmações de pagamento**;
- um cliente pagou e foi estornado no mesmo minuto, e **nunca recebeu a mensagem de estorno**;
- alguns pedidos pagos **nunca geraram mensagem nenhuma**, sem nenhum erro no log.

Ninguém sabe dizer quantos eventos o sistema processa por dia, nem quanto tempo leva do pagamento ao SMS.

## Objetivo

Reconstruir o fluxo evento → notificação para que ele **não perca** e **não duplique**, mesmo com processos morrendo no meio e com o provedor falhando de forma ambígua. Torná-lo **rastreável** ponta a ponta e **medido**.

## Requisitos

1. **Outbox transacional.** A transição do pedido e o registro do evento acontecem **na mesma transação**. Um *relay* separado publica os eventos pendentes na fila e os marca como publicados. Justifique:
   - polling vs. CDC;
   - como o relay evita que duas instâncias publiquem o mesmo lote (ex.: `FOR UPDATE SKIP LOCKED`);
   - o que acontece se ele morrer **entre publicar e marcar**, e por que isso é aceitável.

2. **Consumo seguro.** O consumidor só apaga a mensagem da fila **depois** do commit do que ela produziu. Classifique os erros:
   - **transitório** → retry com backoff exponencial e *jitter*;
   - **permanente** (ex.: `INVALID_PHONE`) → registra e não tenta de novo.

   Depois de `maxReceiveCount = 5`, a mensagem vai para a DLQ. Inclua um comando de redrive.

3. **Idempotência por evento, com prova contra a janela de tempo.** Implemente as duas estratégias, selecionáveis por `DEDUP_STRATEGY`:
   - `time_window`: `order_id` + janela de 60 s, a versão "ingênua";
   - `event_id`: chave gravada com **restrição de unicidade** no banco, na mesma transação do efeito.

   Escreva testes que mostrem a `time_window` falhando **nos dois sentidos**: (a) um redrive da DLQ 2 h depois **duplica**; (b) o pago + estornado em menos de 1 s **perde** o estorno. Os mesmos testes passam com `event_id`.

4. **Sem condição de corrida.** Rode **4 consumidores** em paralelo. Toda mudança de estado da notificação é uma **escrita condicional** (ex.: `UPDATE ... WHERE id = ? AND status = 'PENDING'` e conferir `rowcount`). Nenhum `SELECT` seguido de `UPDATE` decide quem processa. Teste: a mesma mensagem entregue a 10 consumidores ao mesmo tempo resulta em **uma** chamada ao provedor.

5. **Efeito externo idempotente.** A notificação tem a máquina de estados `PENDING → SENDING → SENT | FAILED | UNKNOWN` (mais `SKIPPED` e `SCHEDULED` da regra).
   - Marque `SENDING` **antes** de chamar o provedor.
   - Envie `Idempotency-Key` = id da notificação e `client_reference` = id da notificação.
   - Timeout ou conexão fechada → `UNKNOWN`, **nunca** `FAILED` direto.
   - Um **reconciliador** consulta `GET /messages?client_reference=` para cada `UNKNOWN` (e cada `SENDING` antigo demais): o que foi aceito vira `SENT`; o que não foi volta para `PENDING`.

6. **Decisão sem idempotência no provedor.** Com `IDEMPOTENCY_SUPPORT=off`, o reconciliador continua resolvendo `UNKNOWN`, mas existe uma janela em que reenviar pode duplicar. Decida **por tipo de template**: transacional prefere entregar duas vezes a nunca entregar (*at-least-once*)? E marketing? Implemente a decisão e justifique.

7. **Tracing ponta a ponta.** OpenTelemetry com o contexto propagado por todos os saltos: request HTTP → linha da outbox → atributos da mensagem SQS → consumidor → chamada ao provedor. No Jaeger, **um trace** mostra a jornada de um evento do request da transição até o `202` do provedor. O reconciliador cria um span **ligado** (*span link*) ao trace original.

8. **Logs e métricas.**
   - **Logs:** estruturados em JSON, com `trace_id`, `event_id`, `order_id` e `notification_id` em todas as etapas.
   - **Métricas técnicas:** idade do evento mais antigo não publicado na outbox; profundidade da fila e da DLQ; latência da chamada ao provedor; notificações em `UNKNOWN`.
   - **Métricas de negócio:** eventos produzidos × consumidos × notificações `SENT`, por template. É a métrica que detecta a falha silenciosa.

9. **Números medidos.** Um script de carga aplica **N transições** (você escolhe N ≥ 2.000). Registre em `RESULTADOS.md`:
   - vazão sustentada (eventos/s);
   - latência ponta a ponta p50/p95/p99, da transição ao `202` do provedor;
   - o mesmo com `FAIL_RATE=20` e `AMBIGUOUS_RATE=5`;
   - onde está o gargalo e qual seria a primeira mudança para dobrar a vazão.

   Sem esses números, o desafio não está concluído.

10. **Runbook e decisões escritas.**
    - **`RUNBOOK.md`:** dado um `order_id` cujo cliente diz que não recebeu o SMS, os passos (consultas, painel, trace) para achar a causa em menos de 5 min.
    - **`DECISOES.md`:** até **150 palavras** cada, explicando como o sistema (a) não perde eventos, (b) não duplica envios, (c) é diagnosticado em produção, e (d) por que teto de frequência não é idempotência. É o texto para explicar o sistema numa revisão técnica de arquitetura.

11. **Testes automatizados** cobrindo:
    - regra de notificação (todo o dataset, com relógio injetável);
    - máquina de estados do pedido;
    - as duas falhas da janela de tempo;
    - corrida entre consumidores;
    - morte do relay entre publicar e marcar;
    - `UNKNOWN` resolvido pelo reconciliador nos dois sentidos.

## Critérios de aceite

- **Rodada de caos:** 2.000 transições, com `FAIL_RATE=20`, `AMBIGUOUS_RATE=5`, `IDEMPOTENCY_SUPPORT=on`, o relay morto 2 vezes e um consumidor morto no meio de um lote. Em seguida, o reconciliador e o redrive rodam até zerar `UNKNOWN` e DLQ. No `delivered.jsonl`, **zero** `client_reference` repetido e **toda** notificação esperada presente (as `SKIPPED` e `FAILED` com motivo correto).
- **A mesma rodada com `IDEMPOTENCY_SUPPORT=off`:** `RESULTADOS.md` informa quantas duplicatas houve por template, e o número bate com a decisão do Requisito 6 (ex.: zero em marketing, se marketing foi definido como *at-most-once*).
- **Janela de tempo:** os testes do Requisito 3 falham com `DEDUP_STRATEGY=time_window` e passam com `event_id`.
- O pedido pago e estornado em menos de 1 s gera **duas** mensagens: `PAYMENT_CONFIRMED` e `REFUND_ISSUED`.
- O `CART_RECOVERY` agendado às 22:30 vira `STALE` depois do pagamento das 07:40 e **não sai** às 08:00.
- Um `kill -9` no relay entre publicar e marcar **não perde** nenhum evento. A duplicata que ele gera na fila é absorvida pelo consumidor.
- No Jaeger, um `order_id` escolhido ao acaso mostra o trace completo da transição ao provedor. Um caso `UNKNOWN` mostra o span do reconciliador ligado ao trace original.
- O `RUNBOOK.md` funciona para 3 pedidos sabotados que você escolhe sem olhar (ex.: telefone inválido, mensagem na DLQ, notificação `UNKNOWN` com o reconciliador parado). Em cada um, a causa é achada seguindo só o runbook.
- `RESULTADOS.md` tem os números do Requisito 9, medidos, não estimados.
