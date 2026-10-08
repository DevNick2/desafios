# Desafio — Notificações por Eventos sem Perda e sem Duplicata (Outbox, Escrita Condicional e Efeito Externo Idempotente)

> Nível: **Avançado** (pl↔sr)
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito, não só o desafio em si.
> Organizado em **4 etapas**, cada uma com entrega e critérios próprios. Peça revisão ao fim de cada etapa antes de seguir.

---

## Motivação

Todo sistema que reage a eventos de negócio com uma **ação no mundo real** (mandar SMS, cobrar um cartão, emitir uma nota) tem o mesmo par de exigências: **nenhum evento pode se perder** e **nenhuma ação pode acontecer duas vezes**. Mensageria só garante entrega *pelo menos uma vez*, então as duas exigências precisam ser construídas pela aplicação.

Saber os nomes das peças (DLQ, chave de idempotência, checagem de status) não basta. O que separa um desenho correto de um que parece correto é conhecer **como cada peça falha**:

- deduplicação por **janela de tempo** parece idempotência, mas deixa passar o retry tardio e engole eventos legítimos próximos;
- "ler o status e depois atualizar" tem **condição de corrida** entre consumidores, mesmo dentro de uma transação;
- gravar no banco e publicar na fila são **duas escritas**, e a segunda pode falhar depois do commit da primeira;
- um processo que **parece morto** pode voltar e sobrescrever o trabalho de quem assumiu o lugar dele;
- reconhecer uma reentrega e **devolvê-la à fila** transforma um caso normal num falso erro na DLQ;
- o efeito externo tem um caso que nenhuma fila resolve: o provedor **aceitou** a mensagem, mas a resposta nunca chegou.

Este desafio exercita esses modos de falha **provocando-os de propósito**, com uma versão ingênua ao lado da correta para comparar, e medindo o resultado. Também cobre **tracing distribuído** com OpenTelemetry e o hábito de **ter números medidos** (vazão e latência) do sistema que você opera.

É complementar ao desafio de webhook com parceiro (`2026-09-16-webhook-parceiro-delivery-oauth-sqs`), que trata a **entrada** dos eventos com SQS. Este trata o **produtor** (outbox) e a **saída** (efeito externo) com **RabbitMQ**, para exercitar a semântica de ack/nack, dead-letter exchange e publisher confirms.

## Pré-requisito

Construa, dentro desta pasta, um serviço em **Python 3.12 + FastAPI + PostgreSQL** (todo identificador de código em inglês) com duas partes: a **máquina de estados do pedido** e a **regra de notificação**. Implemente exatamente estas regras.

### 1. Máquina de estados do pedido

Endpoints:
- `POST /customers` e `PATCH /customers/{id}` cadastram e alteram clientes (nome, telefone, `sms_opt_in`).
- `POST /orders` cria o pedido em `CREATED`, com `order_version = 1`.
- `POST /orders/{id}/transitions` com `{"to": "<STATUS>", "expected_version": <int>}` muda o status.

Transições válidas (qualquer outra → `409 INVALID_TRANSITION`):

| De | Para |
|---|---|
| `CREATED` | `PAID`, `ABANDONED` |
| `ABANDONED` | `PAID` (cliente voltou e pagou) |
| `PAID` | `SHIPPED`, `REFUNDED` |
| `SHIPPED` | `DELIVERED`, `REFUNDED` |

O pedido tem `order_version` (inteiro que incrementa a cada transição). A transição só é aplicada se `expected_version` for igual à versão atual; se não for → `409 VERSION_CONFLICT`. Os dois `409` têm significados diferentes para o cliente: `VERSION_CONFLICT` vale tentar de novo depois de reler o pedido; `INVALID_TRANSITION` não adianta repetir.

Toda transição bem-sucedida gera um evento `ORDER_<STATUS>` (ex.: `ORDER_PAID`) com `event_id` (UUID v4), `order_id`, `occurred_at` e `order_version`.

`SHIPPED` exige `tracking_code` no corpo; sem ele → `422 TRACKING_CODE_REQUIRED`.

### 2. Regra de notificação (o que mandar para cada evento)

| Evento | Template | Tipo | Destinatários |
|---|---|---|---|
| `ORDER_PAID` | `PAYMENT_CONFIRMED` | transacional | comprador |
| `ORDER_SHIPPED` | `ORDER_SHIPPED` (inclui `tracking_code`) | transacional | comprador **e** recebedor, se o pedido tiver `recipient_phone` diferente do telefone do comprador |
| `ORDER_REFUNDED` | `REFUND_ISSUED` | transacional | comprador |
| `ORDER_ABANDONED` | `CART_RECOVERY` | marketing | comprador |
| `ORDER_CREATED`, `ORDER_DELIVERED` | nenhuma mensagem | — | — |

Um mesmo evento pode, portanto, gerar **mais de uma** notificação.

Condições, avaliadas nesta ordem para cada destinatário:

1. **Telefone inválido** (não é E.164 brasileiro: `+55`, DDD de 2 dígitos, celular de 9 dígitos começando com 9) → notificação `FAILED` com motivo `INVALID_PHONE`. **Nunca** é reenviada.
2. **Opt-out:** cliente com `sms_opt_in = false` recebe só **transacional**. Marketing → `SKIPPED` com motivo `OPTED_OUT`.
3. **Valor mínimo:** `CART_RECOVERY` só se o total do carrinho for **≥ R$ 50,00** (5000 centavos; R$ 49,99 não recebe) → senão `SKIPPED` / `BELOW_MINIMUM`.
4. **Teto de frequência:** no máximo **1** `CART_RECOVERY` por **telefone** a cada **24 h** (contando os já `SENT`) → senão `SKIPPED` / `FREQUENCY_CAP`.
5. **Horário de silêncio:** marketing não sai entre **21:00 e 08:00** (`America/Sao_Paulo`). Fica `SCHEDULED` para as 08:00 seguintes. Transacional sai a qualquer hora.
6. **Obsolescência:** se, no momento do envio, o pedido já avançou além do estado que gerou a notificação, ela vira `SKIPPED` / `STALE`. Exemplos: `CART_RECOVERY` agendado de um pedido que já foi pago; `ORDER_SHIPPED` de um pedido já `REFUNDED`.

**Cópia no momento da criação.** A notificação grava, ao ser criada, o telefone de destino e o corpo já montado. Se o cliente trocar de telefone depois, você precisa decidir **qual número** recebe uma notificação que ainda não saiu (o gravado ou o atual), implementar essa decisão e justificá-la no `DECISOES.md`. As duas respostas são defensáveis; não ter uma decisão explícita, não.

> Os itens 4 e 5 são **regra de negócio**, não idempotência. O teto de frequência impede duas mensagens *diferentes* legítimas. A idempotência impede a *mesma* mensagem duas vezes. Essa distinção é cobrada no `DECISOES.md`.

Endpoint de consulta: `GET /orders/{id}/notifications` lista as notificações do pedido com destinatário, status e motivo.

### Dataset

Em `seed/`: **30 clientes** e **60 pedidos** (com itens e totais em centavos), contendo estes casos propositais:

- 2 clientes com telefone inválido (um sem o 9 inicial, um com DDD de 1 dígito);
- 3 clientes com `sms_opt_in = false`, um deles com pedido abandonado e outro com pedido pago;
- 1 carrinho abandonado de exatamente **R$ 50,00** e 1 de **R$ 49,99**;
- 2 pedidos abandonados do **mesmo telefone** com 3 h de intervalo (o segundo cai no teto de frequência);
- 1 pedido abandonado às **22:30** (agendado para 08:00) que é **pago às 07:40** (vira `STALE`);
- 1 pedido pago e estornado com **menos de 1 s** de intervalo (os dois eventos são legítimos e geram duas mensagens);
- 1 pedido `SHIPPED` sem `tracking_code` (deve falhar com `422`);
- 3 pedidos com `recipient_phone`: um diferente do comprador (gera **duas** `ORDER_SHIPPED`), um **igual** ao do comprador (gera **uma**), e um com recebedor de telefone inválido (o comprador recebe; o recebedor fica `FAILED`);
- 1 cliente que **troca de telefone** às 23:00, depois de um abandono às 22:30 e antes do envio agendado das 08:00;
- 2 transições **simultâneas** no mesmo pedido `CREATED` (`PAID` e `ABANDONED`, com o mesmo `expected_version`): exatamente uma vence.

Junto, um roteiro `seed/transitions.jsonl` com a sequência de transições a aplicar e o horário simulado de cada uma. O serviço precisa aceitar um **relógio injetável** para os testes de horário; o replayer de apoio envia o horário de cada passo no header `X-Simulated-Now`.

> **O dataset, o roteiro e o replayer já existem** (`seed/`, `support/seed_generator.py` e `support/replay.py`). São peças de apoio, descritas em [`support/APOIO.md`](support/APOIO.md), junto com o contrato que o replayer espera da sua API.

A máquina de estados e a regra de notificação são **núcleo** e são suas.

## Ambiente de execução

Tudo roda com `docker compose`, sem conta em nenhuma nuvem:

| Dependência | Como roda |
|---|---|
| Broker | **RabbitMQ** com management (`rabbitmq:3.13-management`) |
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

Ele grava **cada SMS "entregue"** num log append-only (`delivered.jsonl`), que é a prova usada nos critérios de aceite. O comportamento também muda em tempo real por `POST /admin/config`, sem reiniciar.

> **O provedor fake, o `docker-compose.yml` e os dublês de teste (`support/testing/fakes.py`) já existem.** O que cada um faz e não faz está em [`support/APOIO.md`](support/APOIO.md).

A lógica que o desafio avalia (outbox, consumo, idempotência, máquina de estados da notificação, reconciliação, tracing) é **núcleo** e é sua.

## Contexto

Uma loja online notifica clientes por SMS a partir de eventos de pedido. A versão atual faz o `UPDATE` do pedido e, logo em seguida, publica o evento na fila, e o consumidor deduplica por `order_id` + horário. Três reclamações chegaram na mesma semana:

- clientes receberam **duas confirmações de pagamento**;
- um cliente pagou e foi estornado no mesmo minuto, e **nunca recebeu a mensagem de estorno**;
- alguns pedidos pagos **nunca geraram mensagem nenhuma**, sem nenhum erro no log.

Além disso, a DLQ tem centenas de mensagens que, olhando uma a uma, **já tinham sido entregues** — ninguém consegue separar o que é falha real do que é ruído. Ninguém sabe dizer quantos eventos o sistema processa por dia, nem quanto tempo leva do pagamento ao SMS.

## Objetivo

Reconstruir o fluxo evento → notificação para que ele **não perca** e **não duplique**, mesmo com processos morrendo, travando e voltando no meio, com o broker fora do ar e com o provedor falhando de forma ambígua. Torná-lo **rastreável** ponta a ponta e **medido**.

---

## Etapa 1 — Pré-requisito

**Entrega:** o serviço do Pré-requisito com o dataset carregado, sem fila nenhuma ainda (as notificações podem ser só criadas no banco).

**Critérios:**
- O roteiro `transitions.jsonl` aplicado do zero produz exatamente as notificações esperadas, com status e motivo, incluindo os dois destinatários e o caso da troca de telefone.
- As duas transições simultâneas no mesmo pedido resultam em uma `200` e uma `409 VERSION_CONFLICT` — nunca duas `200`. A decisão é tomada por **escrita condicional** na versão (`UPDATE ... WHERE id = ? AND order_version = ?` e conferir `rowcount`), não por `SELECT` seguido de `UPDATE`.
- A **unicidade das notificações** está garantida por restrição no banco. Descubra quais colunas ela precisa ter para aceitar as duas `ORDER_SHIPPED` do mesmo evento e recusar uma terceira.
- Testes automatizados da máquina de estados do pedido e de toda a regra de notificação, com relógio injetável.

## Etapa 2 — Outbox e consumo

**Entrega:** relay + RabbitMQ + consumidores, ainda sem chamar o provedor (o efeito pode ser só marcar a notificação como pronta para envio).

1. **Outbox transacional.** A transição do pedido e o registro do evento acontecem **na mesma transação**. Um *relay* separado publica os eventos pendentes com **publisher confirms** e só então os marca como publicados. Justifique:
   - polling vs. CDC;
   - como o relay evita que duas instâncias publiquem o mesmo lote (ex.: `FOR UPDATE SKIP LOCKED`);
   - o que acontece se ele morrer **entre publicar e marcar**, e por que isso é aceitável.

2. **Topologia e consumo seguro.** Fila principal, fila de espera de retry e DLQ, com dead-letter exchange. O consumidor usa **ack manual** e só confirma **depois** do commit do que a mensagem produziu. Classifique os erros:
   - **transitório** → `nack` sem requeue, retry com backoff exponencial (uma fila de espera por degrau, ou outra solução que você justifique) até **5 tentativas**, contadas a partir do header `x-death` ou de um header próprio — justifique a escolha;
   - **permanente** (ex.: `INVALID_PHONE`) → registra e não tenta de novo;
   - **reentrega de algo já processado** → não é erro. Decida o que responder ao broker para que ela **não** vá para retry nem para a DLQ.

   Inclua um comando de redrive da DLQ.

3. **Idempotência por evento, com prova contra a janela de tempo.** Duas estratégias, selecionáveis por `DEDUP_STRATEGY`:
   - `time_window`: `order_id` + janela de 60 s, a versão "ingênua";
   - `event_id`: chave gravada com **restrição de unicidade** no banco, na mesma transação do efeito.

   Testes mostram a `time_window` falhando **nos dois sentidos**: (a) um redrive da DLQ 2 h depois **duplica**; (b) o pago + estornado em menos de 1 s **perde** o estorno. Os mesmos testes passam com `event_id`.

4. **Sem condição de corrida, com prova contra a versão ingênua.** Rode **4 consumidores** em paralelo. Duas estratégias, selecionáveis por `CLAIM_STRATEGY`:
   - `select_then_update`: lê o status, dorme 50 ms (para tornar a janela visível) e atualiza;
   - `conditional_update`: `UPDATE ... WHERE id = ? AND status = 'PENDING'` e conferir `rowcount`.

   Teste: a mesma mensagem entregue a 10 consumidores ao mesmo tempo resulta em **mais de um** "envio" com `select_then_update` e em **exatamente um** com `conditional_update`.

**Critérios:**
- **Reentrega não é falha:** republicar à mão 50 mensagens já processadas resulta em zero efeitos novos e **zero mensagens na DLQ**. A DLQ só contém falhas reais.
- **Broker fora do ar:** com o RabbitMQ **parado por 60 s** no meio de uma carga de 500 transições, nenhum evento se perde. O `DECISOES.md` descreve o que aconteceu com a outbox, o relay e os consumidores durante e depois da parada.
- **DLQ indisponível:** se a publicação na DLQ falhar (simule fechando o canal), a mensagem não pode ser perdida nem confirmada. Descreva o caminho que ela faz até a DLQ voltar.
- `kill -9` no relay entre publicar e marcar **não perde** nenhum evento, e a duplicata gerada na fila é absorvida pelo consumidor.
- Os testes do item 3 falham com `time_window` e passam com `event_id`; os do item 4 falham com `select_then_update` e passam com `conditional_update`.

## Etapa 3 — Efeito externo

**Entrega:** o consumidor chamando o provedor fake, com reconciliação.

1. **Máquina de estados da notificação.** `PENDING → SENDING → SENT | FAILED | UNKNOWN`, mais `SKIPPED` e `SCHEDULED` da regra. Liste as transições **proibidas** e garanta cada uma no banco (escrita condicional), não só no código de quem chama.
   - Marque `SENDING` **antes** de chamar o provedor, registrando **quem** pegou a notificação e **quando**.
   - Envie `Idempotency-Key` = id da notificação e `client_reference` = id da notificação.
   - Timeout ou conexão fechada → `UNKNOWN`, **nunca** `FAILED` direto.

2. **Reconciliador.** Consulta `GET /messages?client_reference=` para cada `UNKNOWN` e cada `SENDING` antigo demais (defina o limite): o que foi aceito vira `SENT`; o que não foi volta para `PENDING`.

3. **Consumidor zumbi.** Um consumidor que **não morreu, só travou** pode voltar depois que o reconciliador devolveu a notificação dele para `PENDING` e outro consumidor a enviou. A atualização atrasada do zumbi **não pode** sobrescrever o estado atual. Resolva com um *fencing token* (dono + versão da reserva) conferido em toda escrita.

4. **Decisão sem idempotência no provedor.** Com `IDEMPOTENCY_SUPPORT=off`, o reconciliador continua resolvendo `UNKNOWN`, mas existe uma janela em que reenviar pode duplicar. Decida **por tipo de template**: transacional prefere entregar duas vezes a nunca entregar (*at-least-once*)? E marketing? Implemente a decisão e justifique.

**Critérios:**
- **Teste de cada transição proibida:** nem o reconciliador, nem um consumidor atrasado, conseguem levar `SENT` de volta para `PENDING` ou `SENDING`.
- **Zumbi:** `kill -STOP` num consumidor no meio da chamada ao provedor, por mais tempo que o limite do `SENDING`; o reconciliador reabre, outro consumidor envia, e então `kill -CONT`. O estado final é o do segundo consumidor, e o log mostra a escrita do zumbi sendo recusada.
- `UNKNOWN` é resolvido pelo reconciliador **nos dois sentidos** (aceito → `SENT`; não aceito → `PENDING` → reenviado).
- O pedido pago e estornado em menos de 1 s gera **duas** mensagens: `PAYMENT_CONFIRMED` e `REFUND_ISSUED`.
- O `CART_RECOVERY` agendado às 22:30 vira `STALE` depois do pagamento das 07:40 e **não sai** às 08:00.
- O caso da troca de telefone sai para o número que a sua decisão definiu, e há teste para isso.

## Etapa 4 — Observabilidade, números e caos

1. **Tracing ponta a ponta.** OpenTelemetry com o contexto propagado por todos os saltos: request HTTP → linha da outbox → headers da mensagem no RabbitMQ → consumidor → chamada ao provedor. No Jaeger, **um trace** mostra a jornada de um evento do request da transição até o `202` do provedor. O reconciliador cria um span **ligado** (*span link*) ao trace original.

2. **Logs e métricas.**
   - **Logs:** estruturados em JSON, com `trace_id`, `event_id`, `order_id` e `notification_id` em todas as etapas. Telefone nunca aparece completo.
   - **Métricas técnicas:** idade do evento mais antigo não publicado na outbox; profundidade da fila principal, da de retry e da DLQ; latência da chamada ao provedor; notificações em `UNKNOWN`; escritas recusadas por fencing.
   - **Métricas de negócio:** eventos produzidos × consumidos × notificações `SENT`, por template. É a métrica que detecta a falha silenciosa.

3. **Números medidos.** Um script de carga aplica **N transições** (você escolhe N ≥ 2.000). Registre em `RESULTADOS.md`:
   - vazão sustentada (eventos/s);
   - latência ponta a ponta p50/p95/p99, da transição ao `202` do provedor;
   - o mesmo com `FAIL_RATE=20` e `AMBIGUOUS_RATE=5`;
   - onde está o gargalo e qual seria a primeira mudança para dobrar a vazão.

   Sem esses números, o desafio não está concluído.

4. **Runbook e decisões escritas.**
   - **`RUNBOOK.md`:** dado um `order_id` cujo cliente diz que não recebeu o SMS, os passos (consultas, painel, trace) para achar a causa em menos de 5 min.
   - **`DECISOES.md`:** até **150 palavras** por item, explicando:
     - (a) como o sistema não perde eventos;
     - (b) como não duplica envios;
     - (c) como é diagnosticado em produção;
     - (d) por que teto de frequência não é idempotência;
     - (e) o diagrama da máquina de estados da notificação (Mermaid `stateDiagram-v2`), com as transições proibidas;
     - (f) por que um cache com TTL (ex.: Redis) usado como buffer de escrita não substitui a outbox;
     - (g) por que uma *view* ou uma consulta antes da escrita não garante unicidade, e o que garante;
     - (h) a decisão sobre o telefone trocado e o que ela custa.

     É o texto para explicar o sistema numa revisão técnica de arquitetura.

**Critérios de aceite finais:**
- **Rodada de caos:** 2.000 transições, com `FAIL_RATE=20`, `AMBIGUOUS_RATE=5`, `IDEMPOTENCY_SUPPORT=on`; durante a rodada, o relay é morto 2 vezes, um consumidor é morto no meio de um lote, outro é congelado com `kill -STOP` e solto depois, e o RabbitMQ fica parado por 60 s. Em seguida, o reconciliador e o redrive rodam até zerar `UNKNOWN` e DLQ. No `delivered.jsonl`, **zero** `client_reference` repetido e **toda** notificação esperada presente (as `SKIPPED` e `FAILED` com motivo correto). A DLQ, antes do redrive, contém **só** falhas reais.
- **A mesma rodada com `IDEMPOTENCY_SUPPORT=off`:** `RESULTADOS.md` informa quantas duplicatas houve por template, e o número bate com a decisão da Etapa 3 (ex.: zero em marketing, se marketing foi definido como *at-most-once*).
- No Jaeger, um `order_id` escolhido ao acaso mostra o trace completo da transição ao provedor. Um caso `UNKNOWN` mostra o span do reconciliador ligado ao trace original.
- O `RUNBOOK.md` funciona para 3 pedidos sabotados que você escolhe sem olhar (ex.: telefone inválido, mensagem na DLQ, notificação `UNKNOWN` com o reconciliador parado). Em cada um, a causa é achada seguindo só o runbook.
- `RESULTADOS.md` tem os números medidos, não estimados.
