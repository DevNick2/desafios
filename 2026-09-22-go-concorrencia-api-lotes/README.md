# Desafio — Go concorrente: API de lotes com worker pool e context (Fase 2 de 2)

> Nível: **Intermediário** (jr↔pl)
> **Fase 1 (pré-requisito desta):** [desafios/2026-09-22-go-fundamentos-cli-comissoes](../2026-09-22-go-fundamentos-cli-comissoes/README.md) — faça antes.
> Desafio autônomo — o pré-requisito é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito.

---

## Motivação

A Fase 1 cobriu a linguagem. O motivo real de uma empresa escolher Go é outro: **concorrência barata e previsível**. Goroutine custa poucos kilobytes, channel é primitivo da linguagem e `context` é o padrão de cancelamento que atravessa toda a biblioteca padrão.

Quem vem de Python e Node chega aqui com dois hábitos que atrapalham: tratar `async` como "não bloqueia" (em Go, goroutine é paralelismo real, com corrida de verdade) e ignorar cancelamento (em Go, quem não propaga `context` vaza goroutine). Este desafio existe para você tropeçar nos dois com o detector de corrida ligado.

## Conceitos (leia antes de começar)

**Goroutine não é promise.** `go f()` dispara execução concorrente e **não devolve nada**. Para saber quando terminou, você usa `sync.WaitGroup` ou um channel. Para receber o resultado, um channel.

**Channel é sincronização, não só fila.** Um channel sem buffer bloqueia o remetente até alguém receber — é um encontro marcado. Com buffer, vira fila de capacidade fixa. A escolha muda o comportamento sob carga.

**`context` é o cancelamento.** Toda função que pode demorar recebe `ctx context.Context` como primeiro parâmetro e respeita `ctx.Done()`. Quando o cliente HTTP desconecta, o `http.Request` já traz um contexto cancelado: propagar isso é o que impede o servidor de trabalhar para ninguém.

**Corrida é detectável.** `go test -race` e `go run -race` instrumentam o binário e apontam acesso concorrente não sincronizado. Se dois goroutines escrevem no mesmo map sem proteção, o detector acusa — e sem ele o bug só aparece em produção.

**Dois jeitos de proteger estado:** `sync.Mutex` em volta da estrutura, ou deixar o estado com **um único goroutine** e falar com ele por channel. Go prefere o segundo ("share memory by communicating"), mas o primeiro é mais simples e legítimo.

## Pré-requisito

Construa, dentro desta pasta, uma API HTTP em Go (apenas `net/http`) com **um** endpoint que aplica a mesma regra de comissão da Fase 1 — reimplementada aqui, para esta pasta continuar independente:

> `POST /commissions/calculate` recebe `{"sales": [...]}` e devolve a comissão por vendedor.
>
> Taxas: `ELECTRONICS` 3%, `FURNITURE` 5%, `APPAREL` 7%; `ONLINE` soma 1 ponto percentual; teto de R$ 500,00 por venda; `CANCELLED` não conta; `RETURNED` estorna; acelerador de +10% acima de R$ 50.000,00 no mês; centavos em `int64`, *half-even*.

Sem banco: o estado vive em memória. Endpoint respondendo com JSON e status correto já basta.

## Ambiente de execução

| Dependência | Como roda |
|---|---|
| Go | Toolchain oficial (1.22+), local |
| Bibliotecas | **Apenas a biblioteca padrão** (`net/http`, `context`, `sync`, `encoding/json`, `testing`, `net/http/httptest`) |
| Serviço externo de imposto | **Fake de apoio** em Go, com latência e taxa de falha configuráveis por variável de ambiente |
| Conta / custo | Nenhum |

## Contexto

O financeiro passou a exigir que cada venda tenha o imposto consultado num **serviço externo** antes do cálculo da comissão — um serviço lento (100–400 ms por chamada) e instável (falha em parte das chamadas). Um lote tem centenas de vendas, e processar uma por vez deixa a requisição inviável.

O serviço externo é um fake local que você sobe junto, com latência e taxa de falha controláveis. Ele é peça de **apoio**: o que o desafio avalia — pool, cancelamento, agregação, proteção de estado — é todo seu.

## Objetivo

Transformar o cálculo em **processamento de lote concorrente**: a API aceita o lote, distribui as consultas de imposto entre N workers, respeita cancelamento e prazo, agrega resultados parciais e expõe o status do lote — sem corrida de dados e sem vazar goroutine.

## Requisitos

1. **`POST /batches`** recebe o lote e devolve `202 Accepted` com um `batch_id`; **`GET /batches/{id}`** devolve status (`RUNNING`, `DONE`, `FAILED`, `CANCELLED`), progresso (processados/total) e o resultado quando pronto.
2. **Worker pool** com tamanho configurável (`WORKERS`, padrão 8), consumindo de um channel de tarefas. Não dispare uma goroutine por venda.
3. **`context` propagado** da requisição até a chamada ao serviço externo: **timeout por item** (padrão 1 s) e **deadline do lote** (padrão 30 s), ambos configuráveis.
4. **Cancelamento real:** `DELETE /batches/{id}` cancela o lote em andamento; os workers param em até um item, e o status vira `CANCELLED`.
5. **Sucesso parcial:** falha numa venda não derruba o lote. O resultado traz, por item, o valor calculado **ou** o motivo da falha, e o lote conclui com um resumo (`ok`, `failed`).
6. **Retry com backoff** para falha transitória do serviço externo: máximo 3 tentativas, respeitando o `context` (retry não pode ignorar cancelamento).
7. **Estado protegido:** o registro dos lotes é acessado por vários goroutines. Proteja com `sync.Mutex`/`sync.RWMutex` **ou** com estado confinado a um goroutine dono. Documente qual escolheu e por quê.
8. **Graceful shutdown:** ao receber `SIGTERM`, o servidor para de aceitar novos lotes, espera os em andamento até um prazo (`SHUTDOWN_TIMEOUT`, padrão 10 s) e só então encerra.
9. **Testes com `net/http/httptest`** cobrindo: lote com sucesso, lote com falhas parciais, cancelamento e timeout de item. **`go test -race ./...` precisa passar limpo.**
10. **Medição:** um teste ou benchmark comparando o mesmo lote com `WORKERS=1` e `WORKERS=8`, com os números registrados no README da solução.

## Critérios de aceite

- `go test -race ./...` passa sem nenhum aviso de corrida.
- Lote de 200 vendas com o fake em 200 ms de latência: com `WORKERS=8` o tempo cai perto de 8x em relação a `WORKERS=1` (registre os números medidos).
- Com o fake em 30% de falha, o lote termina como `DONE` com resumo `ok`/`failed` coerente, e cada item falho traz o motivo.
- `DELETE /batches/{id}` no meio do processamento muda o status para `CANCELLED` e as chamadas ao fake cessam em até um item (comprove pelo log do fake).
- Um item que estoura o timeout de 1 s vira falha daquele item, sem afetar os demais.
- Depois de cancelar ou concluir um lote, **o número de goroutines volta ao patamar inicial** (`runtime.NumGoroutine()` antes e depois, num teste).
- `SIGTERM` durante um lote: o processo espera a conclusão ou o prazo, e não corta a requisição no meio de forma abrupta.
- `go.mod` sem nenhuma dependência externa.

## Para discutir depois (não é requisito)

- Channel com buffer ou sem buffer para a fila de tarefas? O que muda quando o consumidor é mais lento que o produtor?
- Você escolheu mutex ou estado confinado num goroutine? Qual o custo de cada um quando o número de lotes simultâneos cresce?
- O que acontece se o cliente HTTP desistir da requisição e você **não** propagar o `context`? Consegue provocar e mostrar?
