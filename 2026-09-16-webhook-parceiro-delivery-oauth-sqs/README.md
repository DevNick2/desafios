# Desafio — Integração por Webhook com Parceiro de Delivery (HMAC, OAuth2, SQS e DE-PARA)

> Nível: **Avançado** (pl↔sr)
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito, não só o desafio em si.

---

## Motivação

Software de operação para restaurantes vive de integração com parceiros de delivery: **webhooks**, **mapeamento DE-PARA**, processamento assíncrono com **SQS** e tolerância a falhas, e **segurança entre sistemas (OAuth)**.

Você já tem resiliência em produção (Strangler Fig, circuit breaker, SNS). Faltam evidências hands-on do que torna integração com parceiro difícil no dia a dia:

- validar que o webhook veio mesmo do parceiro;
- não processar o mesmo pedido duas vezes quando o parceiro reenvia;
- lidar com eventos fora de ordem;
- manter token OAuth válido sem derrubar a integração;
- recuperar pedidos cujo webhook nunca chegou.

## Pré-requisito

Construa, dentro desta pasta, um serviço em **Node.js + TypeScript** (todo identificador de código em inglês) que **converte o pedido do parceiro para o pedido interno** do restaurante. É a camada DE-PARA. Implemente exatamente estas regras:

> **Status** (`partner_status` → `status` interno): `PLACED → RECEIVED`, `CONFIRMED → PREPARING`, `READY_FOR_PICKUP → READY`, `PICKED_UP → DISPATCHED`, `CONCLUDED → DELIVERED`, `CANCELLED → CANCELLED`. Status desconhecido → erro `UNKNOWN_PARTNER_STATUS`.
>
> **Loja:** `merchant_id` do parceiro é convertido para `store_id` interno por uma tabela de configuração. `merchant_id` sem mapeamento → erro `UNMAPPED_MERCHANT`.
>
> **Itens:** o parceiro manda preço em **reais como string** (`"12.90"`); internamente tudo é **centavos inteiros**. Preço da linha = (`unit_price` + soma dos `options[].price`) × `quantity`. `external_code` do item é convertido para `product_id` por tabela; item sem mapeamento **não derruba o pedido**: entra com `product_id = null` e o pedido fica com `mapping_status = PENDING_MAPPING`.
>
> **Descontos** (`benefits[]`): `type` `PERCENT` (sobre o subtotal de itens) ou `FIXED` (valor em reais). Cada benefício tem `sponsor`: `PARTNER` (o parceiro paga, o restaurante recebe o valor cheio) ou `MERCHANT` (sai do restaurante). O pedido interno guarda `discount_merchant_cents` e `discount_partner_cents` separados; o valor a receber do restaurante desconta só o `MERCHANT`.
>
> **Pagamento:** `ONLINE_CREDIT`/`ONLINE_PIX` → `payment_type = PREPAID`; `CASH`/`CARD_ON_DELIVERY` → `payment_type = PAY_ON_DELIVERY`; se `CASH`, guardar `change_for_cents` (troco para).
>
> **Arredondamento:** `PERCENT` arredonda *half-even* para o centavo.

Endpoint mínimo: `POST /partner-orders/translate` (recebe o payload do parceiro e devolve o pedido interno ou o erro).

**Dataset:** 20 payloads do parceiro em JSON, mais as tabelas de mapeamento (`merchant_id → store_id`, `external_code → product_id`), com estes casos propositais: 1 pedido com item de 3 opções pagas; 1 com item sem mapeamento (`PENDING_MAPPING`); 1 com `merchant_id` não mapeado; 1 com dois benefícios, um `PARTNER` e um `MERCHANT`; 1 `PERCENT` cujo arredondamento *half-even* difere do *half-up*; 1 `CASH` com troco; 1 com `partner_status` desconhecido; 2 com preço string com uma casa decimal (`"9.9"`).

A regra de conversão é **núcleo** e é sua.

## Ambiente de execução

Tudo roda com `docker compose`, sem conta em nenhuma nuvem:

| Dependência | Como roda |
|---|---|
| Fila SQS + DLQ | **LocalStack** (SQS) |
| Banco do serviço | PostgreSQL em container |
| Servidor OAuth2 (client credentials) | **Keycloak** ou `mock-oauth2-server` em container |
| **Parceiro de delivery** | **Fake de apoio** (ver abaixo) |
| Conta / custo | Nenhum |

**O parceiro fake** é peça de apoio (pode ser construída com ajuda, conforme a regra de núcleo vs. apoio). Ele tem comportamento controlável por variável de ambiente:

- envia webhooks `POST` assinados para o seu serviço, com **retry** quando você não responde 2xx em 3 s;
- pode mandar o **mesmo evento duplicado**, eventos **fora de ordem** (atualização de status antes da criação) e webhooks com **assinatura inválida**;
- pode **deixar de enviar** um percentual dos webhooks (para exercitar a reconciliação);
- expõe `GET /orders?updated_since=...` e `POST /orders/{id}/acknowledge`, protegidos por token OAuth2, respondendo `401` com token expirado e `429` com `Retry-After` sob taxa configurável;
- registra em log toda chamada recebida, que é a prova usada nos critérios de aceite.

A lógica que o desafio avalia (verificação de assinatura, idempotência, ordenação, cliente OAuth, fila, reconciliação) é **núcleo** e é sua.

## Contexto

O restaurante recebe pedidos de um marketplace de delivery por webhook. Hoje, qualquer lentidão ou erro no processamento faz o parceiro reenviar, gerando pedido duplicado na cozinha. Webhooks perdidos viram pedidos que o cliente pagou e a cozinha nunca viu.

## Objetivo

Construir o fluxo completo de entrada de pedidos do parceiro: receber e autenticar o webhook, responder rápido, processar de forma assíncrona e idempotente, confirmar ao parceiro com OAuth2 e recuperar o que se perdeu.

## Requisitos

1. **Endpoint de webhook** `POST /webhooks/partner`: valida `X-Signature` = HMAC-SHA256 do **corpo bruto** (não do JSON re-serializado) concatenado ao header `X-Timestamp`, com **comparação em tempo constante**. Rejeita com `401` assinatura inválida e timestamp fora de uma janela de **5 minutos** (proteção contra replay).
2. **Rotação de segredo:** aceita dois segredos ativos ao mesmo tempo (atual e anterior), para trocar o segredo sem derrubar a integração.
3. **Responder rápido:** o endpoint só valida, **enfileira no SQS** e responde `202` em menos de **200 ms**; nenhum processamento de negócio no request.
4. **Worker idempotente:** consome a fila e aplica a conversão do pré-requisito. O mesmo `event_id` processado duas vezes não cria nem altera nada. Justifique onde a chave de idempotência é gravada e como isso se comporta se o worker cair entre gravar o pedido e apagar a mensagem.
5. **Eventos fora de ordem:** uma atualização de status que chega antes da criação do pedido não se perde nem cria um pedido incompleto. Uma atualização mais antiga não sobrescreve um status mais novo (use a versão ou o timestamp do evento do parceiro).
6. **Cliente OAuth2 (client credentials):** o token é obtido, **guardado em cache e renovado antes de expirar**; um `401` inesperado dispara **uma** renovação e **um** novo retry, nunca um loop. Chamadas concorrentes não pedem N tokens ao mesmo tempo.
7. **Confirmação ao parceiro:** após processar, chama `POST /orders/{id}/acknowledge`, respeitando `429` + `Retry-After` com backoff.
8. **DLQ e redrive:** mensagem que falha N vezes vai para a DLQ com o motivo; um comando reprocessa a DLQ depois de corrigido o problema (ex.: `UNMAPPED_MERCHANT` resolvido na tabela).
9. **Reconciliação:** um job periódico consulta `GET /orders?updated_since=` e **cria os pedidos cujo webhook nunca chegou**, sem duplicar os que chegaram. Defina e justifique a janela de sobreposição.
10. **Observabilidade:** log estruturado com `event_id`, `partner_order_id` e `store_id` em todas as etapas, e métricas de webhooks recebidos, rejeitados por assinatura, duplicados ignorados, DLQ e recuperados pela reconciliação.
11. **Testes automatizados** cobrindo: regras DE-PARA (todo o dataset), assinatura válida/inválida/expirada/segredo anterior, idempotência, fora de ordem, renovação de token sob concorrência e reconciliação.

## Critérios de aceite

- Com o parceiro fake enviando **cada evento 3 vezes**, cada pedido existe **uma única vez** e recebe **um único** `acknowledge` (conferido no log do fake).
- Com o parceiro fake **omitindo 20%** dos webhooks, depois de uma rodada de reconciliação todos os pedidos do parceiro existem no serviço, sem duplicata.
- Um webhook com assinatura inválida, ou com timestamp de 6 minutos atrás, recebe `401` e não entra na fila.
- Trocar o segredo com o parceiro ainda assinando pelo segredo anterior não gera nenhum `401` durante a janela de rotação.
- Com token expirando a cada 30 s e 10 confirmações simultâneas, o log do servidor OAuth mostra **uma** emissão de token por expiração, não dez.
- Um pedido com `UNMAPPED_MERCHANT` vai para a DLQ e, após incluir o mapeamento e rodar o redrive, é criado corretamente.
- O endpoint de webhook responde em menos de 200 ms (p95) mesmo com o worker parado.
