# Warehouse colunar: custo de consulta como restrição de projeto

**Nível:** Avançado (pl↔sr)

---

## Motivação

Quem vem de banco relacional transacional carrega um reflexo que custa caro em warehouse analítico: tratar a consulta como se fosse grátis e o índice como se fosse a única alavanca. Em warehouse cobrado por **byte varrido**, a modelagem *é* o custo — particionamento, ordem de clustering e projeção de colunas mudam a fatura em uma ordem de magnitude, e nenhuma delas aparece num `EXPLAIN` tradicional.

Este desafio existe para fechar esse gap de duas formas ao mesmo tempo: construir um pipeline analítico que **mede** quanto cada consulta lê, e tomar as decisões de modelagem com esse número na mão em vez de por intuição. O formato colunar, o particionamento e a validação de schema antes da publicação são o conteúdo; o custo é a régua.

---

## Pré-requisito

Antes do desafio, construa o pipeline que será otimizado. **Este código é seu** — a IA não escreve a regra de negócio abaixo.

### O domínio

Um sistema acompanha preços de produtos em várias lojas ao longo do tempo e precisa responder, por dia e por produto, quão competitivo está o preço da sua própria loja.

### Tabela de fatos: `price_observations`

| Campo | Tipo | Observação |
|---|---|---|
| `observed_at` | timestamp | momento da coleta |
| `store_id` | string | `S001` … `S008`; **`S001` é a sua loja** |
| `product_id` | string | `P0001` … `P2000` |
| `category` | string | `electronics`, `books`, `grocery`, `apparel` |
| `price_brl` | decimal(10,2) | preço anunciado |
| `shipping_brl` | decimal(10,2) | frete; `0.00` significa frete grátis |
| `in_stock` | boolean | |

### Regra de negócio — índice de competitividade diário

**1. Preço efetivo.** `effective_price = price_brl + shipping_brl`.

**2. Elegibilidade.** Só entram observações com `in_stock = true`. Observação fora de estoque é descartada do cálculo, não tratada como preço alto.

**3. Uma observação por loja/produto/dia.** Há várias coletas por dia. Vale a **mais recente do dia** (maior `observed_at`). Empate de timestamp exato é duplicata — ver requisito 2 do desafio.

**4. Preço de referência.** Para cada `product_id` e cada dia, `reference_price` = **mediana** dos `effective_price` elegíveis de **todas as lojas exceto `S001`**. Mediana, não média: o dataset tem outliers propositais e a média mente.

**5. Índice.** `competitiveness_index = effective_price(S001) / reference_price`, arredondado em 4 casas.

**6. Classificação.**

| Condição | `status` |
|---|---|
| `index` ≤ 0,95 | `AGGRESSIVE` |
| 0,95 < `index` ≤ 1,05 | `ALIGNED` |
| `index` > 1,05 | `EXPENSIVE` |
| sem observação elegível de `S001` naquele dia | `NO_COVERAGE` |
| `S001` tem observação, mas nenhuma outra loja tem | `NO_REFERENCE` |

A saída do pipeline é uma tabela `daily_competitiveness` com `day`, `product_id`, `category`, `effective_price`, `reference_price`, `competitiveness_index`, `status`.

### Dataset

**Peça para a IA gerar** — é dado de teste, segue esta especificação à risca e não contém nenhuma decisão do desafio:

- **2.000 produtos**, 4 categorias, distribuídos de forma desigual (electronics ~40%, grocery ~30%, apparel ~20%, books ~10%).
- **8 lojas**, **90 dias** consecutivos, **3 coletas por dia** por loja/produto → ~4,3 milhões de linhas.
- Saída em **Parquet**, sem particionamento nenhum (o particionamento é trabalho seu).
- Casos de borda obrigatórios:
  - 1 produto sem nenhuma observação de `S001` nos dias 30 a 39 (exercita `NO_COVERAGE`);
  - 1 produto em que só `S001` reporta, por 5 dias (exercita `NO_REFERENCE`);
  - a loja `S008` para de reportar a partir do dia 61;
  - ~0,5% das linhas com `effective_price` 10× a mediana do produto (exercita mediana vs. média);
  - ~0,2% de linhas **exatamente duplicadas** (mesmo `store_id`, `product_id`, `observed_at`);
  - ~15% das linhas com `shipping_brl = 0.00`;
  - 300 linhas com `price_brl` negativo ou nulo e 200 com `category` fora das quatro válidas (exercita a validação de schema).

---

## Ambiente de execução

Parte 1 roda inteira local, sem conta paga.

| Dependência | Como roda |
|---|---|
| Engine analítico colunar | **DuckDB** (pip ou binário) — é o proxy local do warehouse: colunar, lê Parquet direto e reporta o que leu |
| Formato de arquivo | **Parquet** via `pyarrow` |
| Camada de publicação relacional | **Postgres** em container (opcional, se você escolher publicar fora do Parquet) |
| Pipeline | Python 3 local |
| Gerador do dataset | **Apoio** — a IA pode construir seguindo a especificação acima |
| BigQuery | **Só na Parte 2, opcional** — ver seção própria |

---

## Contexto

O pipeline existe e devolve o número certo. O problema é o resto: a consulta diária varre o dataset inteiro, ninguém sabe quanto isso custaria num warehouse cobrado por consumo, um reprocessamento de um dia duplica linhas na tabela publicada, e linha com dado inválido entra silenciosamente e aparece como preço absurdo três telas depois.

Você assumiu a responsabilidade técnica por esse pipeline.

---

## Objetivo

Transformar o pipeline em algo cujo custo e correção são **medidos, não presumidos**: modelagem colunar justificada por bytes lidos, publicação idempotente e validação de schema com política explícita.

---

## Requisitos — Parte 1 (obrigatória, local)

**1. Linha de base medida.** Antes de otimizar, registre o custo da consulta ingênua: bytes lidos e tempo, com o comando usado. Sem a linha de base, o resto não tem com o que ser comparado.

**2. Deduplicação e "última do dia".** Implemente a regra 3 do pré-requisito. Duplicata exata e "duas coletas no mesmo dia" são problemas diferentes — trate os dois e **escreva por que** a sua escolha de desempate é defensável.

**3. Particionamento e projeção.** Reescreva o layout em Parquet particionado e refaça a consulta diária lendo só o necessário. Requisitos concretos:
   - escolha a **granularidade de partição** (dia, semana ou mês) e justifique com números, não com preferência;
   - escolha a **ordem de ordenação/clustering** dentro da partição e mostre o efeito;
   - meça novamente bytes lidos e tempo, e apresente a comparação com a linha de base numa tabela.

**4. Consulta de um dia vs. de 90 dias.** Mostre que o layout escolhido serve aos dois padrões de acesso, ou admita explicitamente qual dos dois você sacrificou e por quê. Layout que só serve a um padrão é decisão, não acidente — mas precisa estar escrita.

**5. Validação de schema antes de publicar.** As linhas inválidas do dataset precisam ser barradas antes da tabela publicada. Decida e **justifique**: rejeitar o lote inteiro, ou quarentenar linha a linha e publicar o resto? Qual é o critério para escalar de quarentena para rejeição total (ex.: percentual de linhas inválidas)? Registre as linhas barradas com o motivo — contagem agregada não basta para investigar depois.

**6. Reprocessamento idempotente.** Rodar o pipeline duas vezes para o mesmo dia não pode duplicar nada na `daily_competitiveness`, e um backfill de 10 dias precisa ser seguro de repetir. Implemente e **prove com um teste** que roda o mesmo dia duas vezes e compara o resultado.

**7. Estimativa de custo em warehouse.** Com os bytes medidos no requisito 3, estime o que a consulta diária e o backfill de 90 dias custariam num warehouse cobrado por byte varrido, a US$ 6,25 por TiB. Escreva o número para a consulta otimizada e para a ingênua. É esse contraste que torna a modelagem um argumento de negócio.

---

## Parte 2 — opcional, na nuvem (BigQuery)

Só depois da Parte 1 fechada. **Não é necessária para concluir o desafio** — existe porque warehouse cobrado por byte varrido não tem emulador local fiel, e a Parte 1 usa DuckDB como proxy.

- **Conta necessária:** Google Cloud com faturamento ativado.
- **Camada gratuita:** 1 TiB de consulta por mês e 10 GiB de armazenamento. O dataset deste desafio cabe folgado.
- **Custo estimado:** **US$ 0,00** se você respeitar a camada gratuita. O risco real é um `SELECT *` repetido em loop.
- **Alerta de orçamento obrigatório:** configure um budget de **US$ 5** com alerta em 50% **antes** de subir qualquer dado.
- **Teardown obrigatório:** deixe no repositório um script que apaga o dataset e as tabelas, e rode-o ao terminar.

O que fazer: subir a tabela de fatos particionada por `observed_at` e clusterizada por `store_id, product_id`; medir **bytes faturados** com `--dry_run` (que não cobra); comparar com os bytes lidos da Parte 1 e explicar as diferenças; verificar se o particionamento que você escolheu no DuckDB sobrevive à cobrança real do BigQuery, ou se a conclusão muda.

---

## Critérios de aceite

- [ ] Dataset gerado conforme a especificação, com todos os casos de borda presentes e verificáveis.
- [ ] `daily_competitiveness` correta para os 5 `status`, com teste cobrindo `NO_COVERAGE` e `NO_REFERENCE`.
- [ ] Mediana implementada de verdade (não média), com teste provando a diferença nos produtos com outlier.
- [ ] Duplicata exata e múltiplas coletas por dia tratadas, com a regra de desempate escrita.
- [ ] Tabela comparativa de **bytes lidos e tempo**: ingênua × particionada, com os comandos usados.
- [ ] Granularidade de partição e ordem de clustering escolhidas **com número justificando**, não com preferência.
- [ ] Posição escrita sobre o requisito 4 (um dia × 90 dias), inclusive se foi um sacrifício consciente.
- [ ] Política de validação de schema escrita, implementada, e com as linhas barradas registradas com motivo.
- [ ] Teste que roda o mesmo dia duas vezes e prova que não duplica.
- [ ] Estimativa de custo em US$ para consulta diária e backfill, nas duas versões.
- [ ] Se fizer a Parte 2: budget configurado antes dos dados, bytes faturados medidos com `--dry_run`, comparação escrita e script de teardown no repositório, já executado.

---

## Trade-offs para decidir (não há resposta certa, há resposta defendida)

- Partição por dia dá poda fina e gera 90 diretórios com arquivos pequenos. Onde está o seu ponto de equilíbrio, e o que muda se o volume crescer 10×?
- Clusterizar por `product_id` antes de `store_id` favorece um padrão de consulta e penaliza outro. Qual você escolheu servir?
- Mediana exige ver todos os valores do grupo; média é incremental. O que isso significa para um pipeline que precise virar incremental depois?
- Quarentenar linha inválida mantém o pipeline rodando e publica um retrato incompleto. Rejeitar o lote protege a tabela e para a entrega. Qual dos dois erros é mais barato neste domínio?
- Agregado materializado é rápido e precisa ser reprocessado; consulta sob demanda é sempre atual e paga por leitura. Com custo por byte varrido, qual ganha aqui?

---

> **Execução sem IA — apenas autocomplete padrão do editor.** Isso vale para o pré-requisito (o pipeline e a regra de competitividade) e para todo o desafio: particionamento, validação, idempotência, medição e as justificativas escritas são seus. A IA pode construir apenas a peça de **apoio** — o gerador do dataset conforme a especificação —, e pode responder dúvidas conceituais sem entregar a solução. O produto final é o tipo de material que se defende numa revisão técnica de arquitetura: números medidos e decisões justificadas, não só código que roda.
