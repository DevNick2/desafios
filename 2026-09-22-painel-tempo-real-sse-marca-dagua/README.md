# Desafio — Painel em tempo real: SSE, broker idempotente e marca d'água

> Nível: **Avançado** (pl↔sr)
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito, não só o desafio em si.
> **Parte 2 é opcional** e não é necessária para concluir o desafio.

---

## Motivação

Um painel executivo que consolida várias origens quase em tempo real parece simples no papel. O desenho já existe — SSE em vez de WebSocket, publicação pós-commit, polling com marca d'água, idempotência no consumo — mas nada disso foi implementado.

São quatro mecanismos que só se aprendem de verdade quebrando:

- **SSE** com snapshot inicial, reconexão e heartbeat (não é "só mandar `text/event-stream`");
- **marca d'água** com sobreposição, que existe porque a ordem de escrita não é a ordem de commit;
- **idempotência de consumo**, que é o que torna a sobreposição e o retry inofensivos;
- **convergência**: o painel precisa chegar ao número certo mesmo depois de o stream cair, o broker reiniciar ou alguém escrever direto no banco.

## Pré-requisito

Construa, dentro desta pasta, uma API em **Python + FastAPI** (todo identificador de código em inglês) para uma rede de **oficinas mecânicas** que agenda ordens de serviço. Implemente exatamente estas regras:

> **Ordem de serviço** (`service_order`): `id`, `unit_id`, `customer_id`, `service_type`, `scheduled_at`, `status`, `amount_cents`, `created_at`, `updated_at`.
>
> **Preço base** por `service_type`: `REVIEW` R$ 250,00; `OIL_CHANGE` R$ 180,00; `ALIGNMENT` R$ 120,00; `DIAGNOSTIC` R$ 90,00.
>
> 1. **Desconto fidelidade:** −10% se o cliente tiver **3 ou mais ordens `DONE`** nos últimos 180 dias.
> 2. **Acréscimo de sábado:** +15% se `scheduled_at` cair num sábado. Aplica-se **depois** do desconto.
> 3. **Arredondamento** em centavos inteiros, *half-even*.
> 4. **Transições de status válidas:** `SCHEDULED → IN_PROGRESS → DONE`; `SCHEDULED` ou `IN_PROGRESS` → `CANCELLED`. Qualquer outra devolve erro `INVALID_TRANSITION`.
> 5. **Taxa de cancelamento:** cancelar com menos de 24 h de antecedência gera `cancellation_fee_cents` = 30% do `amount_cents`; com 24 h ou mais, zero.
> 6. **`updated_at` é obrigatório e muda em toda alteração** — é o que o desafio usa como marca d'água. Sem trigger ou equivalente, o desafio não funciona.

Endpoints mínimos: `POST /service-orders`, `PATCH /service-orders/{id}/status`, `GET /service-orders`.

**Dataset:** 40 ordens distribuídas em 4 unidades e 15 clientes, com estes casos propositais:

- 1 cliente com exatamente 3 ordens `DONE` nos últimos 180 dias (fronteira do desconto) e 1 com 2 (não desconta);
- 1 ordem com 4 ordens `DONE` fora da janela de 180 dias (não desconta);
- 3 ordens em sábado, uma delas também com desconto fidelidade (as duas regras compostas);
- 2 cancelamentos, um com 23 h de antecedência e outro com 25 h;
- 5 ordens compartilhando exatamente o mesmo `updated_at` (para o `LIMIT` do polling cair no meio do empate);
- pelo menos 8 ordens por unidade, para os KPIs por unidade terem massa.

A API e as regras são **núcleo** e são suas. O dataset é apoio.

## Ambiente de execução

Tudo com `docker compose`, sem conta em nenhuma nuvem:

| Dependência | Como roda |
|---|---|
| Banco da aplicação | PostgreSQL em container |
| Cache + fan-out entre instâncias | Redis em container |
| Segunda instância da API | Segundo container do seu serviço, atrás de um proxy simples (nginx ou Caddy) |
| Banco "de terceiro" (Parte 2) | Segundo PostgreSQL com `wal_level = logical` |
| Conta / custo | Nenhum |

## Contexto

A diretoria quer um painel com os números da operação atualizando sozinho: ordens agendadas para hoje, em andamento, concluídas, canceladas e receita do dia, por unidade.

O painel tem três realidades desconfortáveis:

1. Nem toda escrita passa pela sua API — há carga manual e script de correção direto no banco.
2. O navegador de quem está com o painel aberto cai, troca de rede e volta.
3. O serviço reinicia no meio do expediente, e ninguém pode perceber isso olhando o número.

## Objetivo

Implementar o fluxo completo: a API publica o evento **depois do commit**, um polling incremental cobre o que não passa pela API, um **broker único e idempotente** recebe as duas origens, mantém o estado agregado em cache e empurra por **SSE** para os painéis conectados — de forma que o número na tela **convirja para o correto** depois de qualquer falha.

## Requisitos

1. **`GET /dashboard/stream?unit_id=`** em SSE: o primeiro evento é o **snapshot** dos KPIs; os seguintes são atualizações. Heartbeat a cada 20 s. Suporte a `Last-Event-ID` na reconexão, retomando sem perder nem repetir atualização.
2. **KPIs, não linhas.** O evento carrega os números agregados por unidade e o instante do cálculo (`calculated_at`), nunca a ordem de serviço crua.
3. **Broker como ponto único de publicação**, com idempotência por `(entity, id, updated_at)`: reprocessar o mesmo evento não altera o KPI. Ele grava no cache **e** publica no hub.
4. **Publicação pós-commit** na API: transação que falha não pode emitir evento. Pode ser publicação após commit confirmado ou outbox na mesma transação — a escolha é sua e precisa estar justificada no README da solução.
5. **PollingService** a cada 30 s: lê a marca d'água persistida em `polling_control (origin, last_watermark)`, consulta `WHERE updated_at > last_watermark - overlap ORDER BY updated_at LIMIT N`, publica no broker e **só então** grava a nova marca. Falha na publicação mantém a marca.
6. **Sobreposição configurável** (`overlap`, padrão 2 min) e `LIMIT` que não corta empate de `updated_at` pela metade — o dataset tem 5 registros com o mesmo valor justamente para isso.
7. **Aquecimento no boot:** carregar a janela corrente para o cache **sem publicar**, antes de ligar o polling. Reiniciar o serviço não pode inundar os painéis conectados.
8. **Duas instâncias.** Rode duas réplicas atrás do proxy. O fan-out do evento entre elas vai pelo Redis, e o polling roda em **uma só** (eleição por `pg_try_advisory_lock` ou equivalente), não nas duas.
9. **Observabilidade:** log estruturado e contadores de eventos publicados, ignorados por idempotência, relidos por sobreposição e conexões SSE abertas.
10. **Testes automatizados** cobrindo: regra de preço (todos os casos do dataset), transições inválidas, idempotência, retomada da marca d'água após falha de publicação, e reconexão SSE com `Last-Event-ID`.

## Critérios de aceite

Cada um é um experimento que você roda e registra o resultado no README da solução:

- **Escrita fora da API:** um `UPDATE` direto no banco muda um KPI no painel em no máximo um ciclo de polling, sem reiniciar nada.
- **Convergência após queda:** derrube o broker, faça 10 alterações (metade pela API, metade direto no banco), suba o broker — o painel chega aos mesmos números de uma consulta `SELECT` de conferência, sem intervenção manual.
- **Sem evento fantasma:** uma transação que falha depois de "quase" concluir não produz nenhum evento no painel.
- **Duplicata não conta duas vezes:** publique o mesmo evento 5 vezes; os KPIs ficam idênticos.
- **Sobreposição não duplica:** com `overlap = 2 min`, cada ciclo relê registros, e o contador de "ignorados por idempotência" cresce enquanto os KPIs não mudam.
- **Empate de `updated_at`:** com `LIMIT` menor que o número de registros empatados, nenhum registro é pulado entre os ciclos.
- **Restart limpo:** reiniciar o serviço com painéis abertos não gera rajada de atualizações nem número errado; o `calculated_at` continua avançando.
- **Duas instâncias:** um evento gerado na instância A chega a um painel conectado na instância B, e o polling roda uma vez por ciclo no conjunto, não duas.
- **Reconexão:** desconecte a rede por 1 minuto durante alterações; ao voltar, o painel converge (via `Last-Event-ID` ou novo snapshot), sem número duplicado.

---

## Parte 2 — CDC sobre o WAL (opcional)

Só comece depois da Parte 1. Aqui entra a segunda origem: um **banco de terceiro** que você não pode alterar — sem `updated_at`, sem trigger, sem acesso ao código.

Suba um segundo PostgreSQL com `wal_level = logical`, crie uma tabela de lançamentos financeiros (`id`, `service_order_id`, `amount_cents`, `paid_at`) e alimente por scripts, simulando o sistema do parceiro.

1. **Consumir a replicação lógica** (slot + `pgoutput` ou `wal2json`), transformar cada mudança em evento e publicar no **mesmo broker** da Parte 1, que passa a ter três origens.
2. **`DELETE` também conta:** apague uma linha e mostre que o KPI reage — é o que o polling por marca d'água não consegue fazer.
3. **Medir a latência** entre o commit na origem e a atualização no painel, comparando com o ciclo de 30 s do polling.
4. **Ver o risco na prática:** pare o consumidor por alguns minutos com escrita ativa e mostre o slot acumulando WAL (`pg_replication_slots`, `pg_wal_lsn_diff`). Registre o tamanho retido e explique o que acontece se ninguém perceber.
5. **Retomada:** derrube o consumidor no meio de um lote e prove que, ao voltar, ele continua do LSN confirmado, sem perder nem duplicar.

**Critério de aceite da Parte 2:** um `INSERT`, um `UPDATE` e um `DELETE` na base de terceiro aparecem no painel sem nenhuma alteração no schema dela, e o README da solução traz o número medido da latência e do WAL retido no teste de consumidor parado.

## Para discutir depois (não é requisito)

- Em que volume o polling de 30 s deixa de fazer sentido e o CDC passa a se pagar?
- Se o painel precisasse de 1 segundo de latência em vez de 30, o que mudaria primeiro?
- Que parte desta arquitetura você removeria numa primeira versão, sem perder a confiança do número?
