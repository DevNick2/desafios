# Desafio — Go do zero: CLI de comissões (Fase 1 de 2)

> Nível: **Iniciante**
> **Fase 2:** [desafios/2026-09-22-go-concorrencia-api-lotes](../2026-09-22-go-concorrencia-api-lotes/README.md) — só comece depois desta.
> Desafio autônomo — o pré-requisito é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito.

---

## Motivação

Go é presença crescente em backends e ferramentas de infraestrutura, e o conhecimento hoje é zero. Como já existem 10+ anos de backend em Python e Node, o que falta **não** é lógica de programação: é o jeito de Go fazer as mesmas coisas — erro como valor em vez de exceção, interfaces implícitas, ponteiros explícitos, e uma biblioteca padrão que dispensa framework.

Esta fase cobre a linguagem. A concorrência, que é onde Go realmente se diferencia, fica para a Fase 2.

## Conceitos (leia antes de começar)

**Erro é valor, não exceção.** Em Go não existe `try/except`. Funções devolvem `(resultado, error)` e você checa `if err != nil` na hora. Parece repetitivo vindo de Python, mas o efeito é que todo caminho de falha fica visível no código. `panic` existe, mas é para erro de programação irrecuperável — não é o `raise` do Python.

**Zero value.** Toda variável nasce com um valor útil: `0` para números, `""` para string, `nil` para ponteiro, slice e map. Não existe `undefined`. Isso muda como você escreve construtores e validações.

**Slice não é array.** `[]int` é uma janela sobre um array, com tamanho e capacidade. Passar um slice para uma função passa essa janela: alterar um elemento afeta o original, mas dar `append` pode ou não afetar. É a primeira pegadinha real para quem vem de listas Python.

**Interface é implícita.** Não existe `implements`. Se o seu tipo tem os métodos que a interface exige, ele já satisfaz a interface. Isso permite escrever a interface **no consumidor**, com só os métodos que ele usa.

**Ponteiro é explícito.** `*Sale` e `Sale` são tipos diferentes. Métodos com receptor ponteiro (`func (s *Sale) ...`) podem alterar o valor; com receptor valor, trabalham numa cópia.

**`defer`** agenda uma chamada para quando a função retornar — o jeito idiomático de fechar arquivo e liberar recurso.

## Pré-requisito

Crie o módulo (`go mod init`) e um arquivo `main.go` que apenas leia o CSV de entrada e imprima quantas linhas leu. Só isso: é para você resolver `go.mod`, `go run`, importação de pacote e `encoding/csv` antes do problema de verdade.

## Ambiente de execução

| Dependência | Como roda |
|---|---|
| Go | Toolchain oficial (1.22+), instalação local |
| Bibliotecas | **Apenas a biblioteca padrão** — sem framework, sem dependência externa |
| Conta / custo | Nenhum |

## Contexto

Uma rede de lojas paga comissão aos vendedores. Hoje o cálculo sai de uma planilha manual, e o financeiro quer um programa de linha de comando que leia o arquivo de vendas e produza o relatório de comissões do mês.

## Objetivo

Escrever uma CLI em Go que lê o CSV de vendas, aplica a regra de comissão e imprime o relatório por vendedor — em texto ou JSON, conforme a flag.

Regra completa, para implementar exatamente como está:

> **Comissão por venda** = `amount_cents × taxa da categoria`, onde `ELECTRONICS` = 3%, `FURNITURE` = 5%, `APPAREL` = 7%.
>
> 1. **Bônus de canal:** venda com `channel = ONLINE` soma **1 ponto percentual** à taxa da categoria (ex.: `ELECTRONICS` online = 4%).
> 2. **Teto por venda:** a comissão de uma única venda nunca passa de **R$ 500,00**.
> 3. **Status:** `CANCELLED` não gera comissão. `RETURNED` gera comissão **negativa** (estorno do valor que seria pago). `COMPLETED` é o caso normal.
> 4. **Acelerador mensal:** se o total vendido pelo vendedor no mês (somando só `COMPLETED`) passar de **R$ 50.000,00**, a comissão total dele recebe **+10%**. Exatamente R$ 50.000,00 **não** aciona.
> 5. **Arredondamento** em centavos inteiros, *half-even*, aplicado no valor de cada venda antes de somar.

**CLI:** `go run . --input sales.csv --month 2026-09 [--format text|json]`. O relatório traz, por vendedor: total vendido, comissão base, indicador de acelerador e comissão final; e uma linha de totais. `--month` filtra por `sold_at`.

**Dataset** (`sales.csv`, 60 linhas, 6 vendedores, campos `id`, `seller_id`, `category`, `channel`, `status`, `amount_cents`, `sold_at`), com estes casos propositais:

- 1 venda cuja comissão passaria de R$ 500,00 e precisa ser cortada pelo teto;
- 1 vendedor com total mensal de **exatamente** R$ 50.000,00 (não acelera) e outro com R$ 50.000,01 (acelera);
- 1 venda `RETURNED` de categoria `APPAREL` (estorno) e 2 `CANCELLED`;
- 1 venda `ONLINE` de `ELECTRONICS` (bônus de canal);
- 1 valor cujo arredondamento *half-even* difere do *half-up*;
- 3 vendas de outro mês, para provar que o filtro funciona;
- 1 linha com `amount_cents` não numérico e 1 com categoria desconhecida, para exercitar erro.

## Requisitos

1. **`go.mod` próprio** e código organizado em mais de um arquivo (ex.: leitura, regra, saída) — não um `main.go` de 300 linhas.
2. **Tipos de domínio:** `struct` para a venda e para a linha do relatório, com os campos tipados (dinheiro em `int64` de centavos, nunca `float64`).
3. **Erro como valor:** nenhuma função entra em `panic` por dado ruim. Linha inválida gera erro descritivo com `fmt.Errorf` e `%w`, e o programa decide se pula a linha (reportando ao final) ou aborta — sua escolha, documentada no README da solução.
4. **Erro nomeado:** ao menos um erro do domínio (ex.: `ErrUnknownCategory`) verificável com `errors.Is`.
5. **Interface no consumidor:** a função que calcula o relatório recebe uma `interface` de fonte de dados (algo como `SalesSource`), para o teste injetar dados sem tocar em arquivo. O CSV é só uma implementação.
6. **Saída em dois formatos** pela flag `--format`, usando `encoding/json` para o JSON e `text/tabwriter` para a tabela.
7. **Testes de tabela** (`table-driven tests`) cobrindo cada regra: taxa por categoria, bônus de canal, teto, estorno, fronteira do acelerador e arredondamento.
8. **`gofmt` e `go vet` limpos**, e `go test ./...` passando.

## Critérios de aceite

- `go test ./...` passa, e os testes cobrem todos os casos de borda do dataset.
- A venda que estoura o teto aparece com exatamente R$ 500,00 de comissão.
- O vendedor com R$ 50.000,00 cravados **não** recebe o acelerador; o de R$ 50.000,01 recebe.
- A venda `RETURNED` reduz a comissão do vendedor, e as `CANCELLED` não aparecem em nenhum total.
- `--month 2026-08` muda o resultado (as vendas de outro mês entram e as de setembro saem).
- As duas linhas defeituosas do CSV não derrubam o programa: viram erro reportado.
- `--format json` produz JSON válido com os mesmos números da saída em texto.
- Nenhuma dependência externa em `go.mod`.

## Para discutir depois (não é requisito)

- Onde você sentiu falta de exceção, e o que o `if err != nil` te obrigou a decidir que antes passava batido?
- Por que dinheiro em `int64` e não `float64`? Consegue provar o problema com um teste?
- Você declarou a interface junto do consumidor ou junto da implementação? Qual a diferença prática em Go?
