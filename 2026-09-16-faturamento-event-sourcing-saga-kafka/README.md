# Desafio — Faturamento com Event Sourcing, CQRS e Saga sobre Kafka

> Nível: **Avançado** (pl↔sr)
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito, não só o desafio em si.

---

## Motivação

Gap identificado num processo seletivo real para arquiteto de software (detalhes da empresa omitidos de propósito): a vaga é a construção de uma **plataforma de faturamento do zero** com arquitetura orientada a eventos, pedindo explicitamente **Kafka, Event Sourcing, CQRS e Saga**. Você já tem experiência real com mensageria (SNS/SQS, RabbitMQ) e com Strangler Fig + circuit breaker, mas nenhuma implementação hands-on de:

- estado derivado de um **log de eventos imutável** (em vez de uma linha atualizada no banco);
- **projeções** reconstruíveis do zero a partir desse log;
- uma **transação distribuída com compensação** (Saga) atravessando serviços que falham.

Faturamento é o domínio clássico para esses padrões: dinheiro exige auditoria completa, operações não podem ser aplicadas duas vezes e uma falha no meio do fluxo precisa ser desfeita de forma rastreável.

## Pré-requisito

Construa, dentro desta pasta, uma API em **Node.js + TypeScript** (NestJS recomendado, mas não obrigatório; todo identificador de código em inglês) que calcula a **cotação de faturamento de uma reserva de viagem**. Implemente exatamente esta regra, não uma variação livre:

> **Itens da reserva** (`item_type`): `HOTEL` (preço por noite × `nights`), `FLIGHT` (preço fixo), `TRANSFER` (preço fixo).
>
> 1. `subtotal` = soma dos itens.
> 2. `service_fee` = 5% sobre itens `HOTEL` + 3% sobre itens `FLIGHT` + 0% sobre `TRANSFER`.
> 3. `service_tax` (imposto sobre serviço) = 5% **apenas sobre o `service_fee`**.
> 4. `total` = `subtotal` + `service_fee` + `service_tax`.
> 5. **Parcelamento** (`installments`, de 1 a 10):
>    - `total` < R$ 1.000,00 → só 1x.
>    - `total` ≥ R$ 1.000,00 → até 6x sem juros (parcela = `total / n`).
>    - 7x a 10x → juros compostos de **1,99% a.m.**, com parcela = `total × i / (1 − (1 + i)^−n)`.
>    - Pedido acima do permitido → erro `INSTALLMENTS_NOT_ALLOWED`.
> 6. **Multa de cancelamento** (`cancellation_fee`) sobre o `total`, pela antecedência em relação à data do primeiro item (`starts_at`): mais de 7 dias → 0%; entre 48 h e 7 dias → 20%; menos de 48 h → 50%.
> 7. **Arredondamento:** todo valor monetário em centavos inteiros (`amount_cents`), arredondamento *half-even* em cada etapa (não só no fim). A soma das parcelas precisa bater com o total parcelado; a diferença de centavo vai na **última** parcela.

Endpoints mínimos: `POST /bookings/quote` (recebe itens + `installments`, devolve `subtotal`, `service_fee`, `service_tax`, `total`, `installment_plan`) e `POST /bookings/{id}/cancellation-quote` (recebe `requested_at`, devolve `cancellation_fee`).

**Dataset:** 12 reservas (`booking_id`, `customer_id`, `items[]`, `starts_at`, `installments`), com estes casos propositais:

- 1 reserva cujo `total` dá **exatamente** R$ 1.000,00 (fronteira do parcelamento sem juros).
- 1 reserva com `total` de R$ 999,99 pedindo 2x (deve falhar com `INSTALLMENTS_NOT_ALLOWED`).
- 1 reserva em 10x (juros compostos).
- 1 reserva só com `TRANSFER` (`service_fee` e `service_tax` zerados).
- 1 reserva em que o arredondamento *half-even* muda o centavo final em relação ao *half-up*.
- 3 reservas com `starts_at` posicionado para cair em cada faixa de multa (> 7 dias, 48 h–7 dias, < 48 h) a partir de uma data de referência fixa `2026-10-01T12:00:00-03:00`.
- 3 reservas do mesmo `customer_id`, para exercitar consultas agregadas por cliente no read model do desafio.

Essa API é construída do zero para este desafio, não é reaproveitamento de nenhum outro projeto seu. É ela que o desafio transforma em serviço orientado a eventos.

## Contexto

A cotação vira uma **fatura real** quando a reserva é confirmada. Confirmar uma reserva é uma operação distribuída em três passos, cada um num "serviço" diferente:

1. **Reservar inventário** num fornecedor externo (hotel/companhia aérea) — `ReserveInventory` / compensação `ReleaseInventory`.
2. **Autorizar pagamento** num gateway externo — `AuthorizePayment` / compensação `VoidAuthorization`.
3. **Emitir a fatura** no seu próprio serviço de faturamento — `IssueInvoice` (último passo; se ele falhar, os dois anteriores precisam ser compensados).

O fornecedor e o gateway **não são seus** — simule os dois como serviços fake locais com comportamento controlável por variável de ambiente (taxa de falha, latência, e um modo "timeout que na verdade executou", em que a operação é aplicada mas a resposta nunca chega). Esses fakes são peças de **apoio**; a Saga, o event store, as projeções e a regra de faturamento são **núcleo** e são seus.

Infra local via `docker compose`: **Kafka** (ou Redpanda, que é compatível com a API do Kafka), **PostgreSQL** (event store) e **MongoDB** (read model).

## Objetivo

Implementar o faturamento como **agregado event-sourced** publicado em Kafka, com **read model CQRS** reconstruível e a confirmação de reserva orquestrada por uma **Saga com compensação**, de forma que nenhum dinheiro seja cobrado duas vezes, nenhuma fatura fique órfã e todo estado seja auditável a partir dos eventos.

## Requisitos

1. **Agregado `Invoice` event-sourced.** O estado nunca é salvo diretamente, só reconstruído aplicando eventos (`InvoiceDrafted`, `InvoiceIssued`, `InstallmentPlanDefined`, `InvoiceCancelled`, `CancellationFeeCharged`). Invariantes no agregado: não emite fatura cancelada, não cancela duas vezes, multa calculada pela regra do pré-requisito.
2. **Event store em PostgreSQL** append-only, com `stream_id`, `version`, `event_type`, `event_version`, `payload`, `occurred_at`, e **concorrência otimista**: gravar com `expected_version` e rejeitar conflito com erro explícito (`CONCURRENCY_CONFLICT`), sem sobrescrever.
3. **Publicação confiável via outbox.** O evento é gravado no event store e numa tabela outbox **na mesma transação**; um relay publica no Kafka. Proibido o "dual write" (gravar no banco e publicar no Kafka em chamadas separadas sem garantia).
4. **Tópicos e particionamento.** Chave de partição = `booking_id`, garantindo ordem por reserva. Justifique no README da sua solução o número de partições e o que acontece com a ordem se ele mudar.
5. **Projeção CQRS em MongoDB** (`invoices_by_customer`, com totais em aberto e cancelados por cliente), atualizada por um consumer **idempotente**: reprocessar o mesmo evento não altera o resultado (controle por `event_id` ou pela versão do stream).
6. **Rebuild da projeção.** Um comando apaga o read model e o reconstrói do zero relendo os eventos, chegando ao mesmo estado.
7. **Saga orquestrada** para `ConfirmBooking`, com estado persistido (`STARTED → INVENTORY_RESERVED → PAYMENT_AUTHORIZED → COMPLETED`, ou `COMPENSATING → COMPENSATED`). Deve **retomar do ponto certo** se o processo cair no meio (mate o processo entre dois passos e suba de novo).
8. **Compensação** na ordem inversa quando qualquer passo falha, com as próprias compensações idempotentes e com retry (compensar duas vezes não estorna duas vezes).
9. **Modo "timeout que executou".** Quando o gateway aplica a autorização mas a resposta não chega, a Saga não pode autorizar de novo às cegas. Use **chave de idempotência** na chamada e uma consulta de status antes de repetir.
10. **Dead Letter Queue.** Evento que falha no consumer após N tentativas vai para um tópico DLQ com o motivo, sem travar a partição; um comando reprocessa a DLQ.
11. **Evolução de schema.** Introduza `InvoiceIssued` v2 (novo campo `currency`, padrão `BRL`) e implemente *upcasting* na leitura, de modo que eventos v1 já gravados continuem funcionando sem migração do event store.
12. **Testes automatizados** cobrindo: regra de faturamento (todos os casos do dataset), conflito de concorrência, idempotência do consumer, rebuild da projeção, Saga com falha em cada um dos três passos e retomada após crash.

## Critérios de aceite

- Com o gateway fake em **100% de falha**, confirmar uma reserva termina em `COMPENSATED`, com o inventário liberado e **nenhuma** fatura emitida — verificável pelos eventos do stream.
- Com o gateway em **modo "timeout que executou"**, a reserva termina com **uma única** autorização no gateway fake (conte pelo log do fake), mesmo com retries.
- Matando o processo da Saga logo após `INVENTORY_RESERVED` e subindo de novo, a Saga continua do passo de pagamento, sem reservar o inventário outra vez.
- Publicar o mesmo evento duas vezes no tópico não muda os totais de `invoices_by_customer`.
- Apagar o MongoDB e rodar o rebuild produz exatamente o mesmo read model de antes, comparado por um teste.
- Duas confirmações concorrentes na mesma reserva resultam em uma aceita e uma rejeitada com `CONCURRENCY_CONFLICT`, nunca em duas faturas.
- Eventos `InvoiceIssued` v1 gravados antes da mudança continuam sendo lidos corretamente, agora com `currency = BRL`.
- A soma das parcelas de todas as reservas do dataset bate centavo a centavo com o total parcelado.

## Para discutir depois (não é requisito)

- Saga orquestrada vs. coreografada: o que mudaria neste fluxo e qual você defenderia numa entrevista?
- Quando Event Sourcing **não** vale a pena? Aponte pelo menos uma parte desta plataforma em que você não usaria.
- Snapshots: a partir de quantos eventos por stream você introduziria e como mediria isso?
