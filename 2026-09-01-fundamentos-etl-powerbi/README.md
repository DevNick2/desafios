# Fundamentos: ETL + Power BI (Fase 1 de 2)

**Nível:** Iniciante

**Fase 2 (depende desta):** [desafios/2026-09-01-arquitetura-migracao-erp-etl](../2026-09-01-arquitetura-migracao-erp-etl/README.md)

## Motivação

Você já tem um desafio Especialista pausado (Fase 2) sobre desenho de arquitetura de migração de ERP com pipeline de ETL — mas você não tem nenhuma experiência prática com ETL nem com Power BI ainda, então esse desafio quebra em duas fases: aqui você constrói a base hands-on (um pipeline ETL de verdade, rodando, e um dashboard real em Power BI); na Fase 2 você desenha a arquitetura de nível sênior/entrevista em cima dessa base.

Você já domina Python e Postgres — essa fase reaproveita isso: o "T" e o "L" do ETL vão usar ferramentas que você já conhece, o novo aqui é o padrão ETL em si e a ferramenta de BI.

## Conceitos (leia antes de começar)

**ETL vs. ELT.** ETL (Extract, Transform, Load) transforma os dados *antes* de carregar no destino — a transformação acontece "fora", geralmente em um script ou ferramenta dedicada. ELT (Extract, Load, Transform) carrega os dados brutos primeiro e transforma *dentro* do destino (normalmente um data warehouse com poder de processamento, tipo BigQuery/Snowflake). Para pipelines pequenos/médios, ETL com um script é mais simples de entender e depurar — é onde este desafio começa.

**Os 3 passos, sem mistério:**
- **Extract** — ler os dados da fonte original (arquivo, API, banco). Nada de transformação aqui, só leitura.
- **Transform** — limpar (valores nulos, duplicados, tipos errados), converter formatos, calcular campos derivados (ex.: total = quantidade × preço), e **validar** (é aqui que "qualidade de dados desde a origem" acontece de verdade — não é uma frase bonita, é um passo concreto que rejeita ou sinaliza dado ruim antes dele contaminar o destino).
- **Load** — gravar o resultado transformado no destino (aqui: Postgres).

**Ferramenta de orquestração (ex.: Airflow).** Quando um pipeline ETL cresce (várias etapas, dependências entre elas, precisa rodar em horários fixos, precisa de retry se falhar), um script solto vira difícil de manter — é aí que entram ferramentas como Airflow, que orquestram múltiplas tarefas com dependências, agendamento e observabilidade. Você não vai instalar Airflow neste desafio — só entender por que ele existe, pra decidir com propriedade "build vs. buy" na Fase 2.

**Power BI, por cima.** É uma ferramenta de BI (Business Intelligence) da Microsoft — você conecta a uma fonte de dados (neste caso, o Postgres onde você vai carregar os dados) e constrói visualizações (gráficos, tabelas, KPIs) sem escrever código. O equivalente do "T" do ETL dentro do Power BI se chama Power Query — mas neste desafio a transformação já vai ter acontecido no seu script Python; o Power BI aqui é só a camada de visualização.

## Objetivo

1. **Escolher ou gerar uma fonte de dados simples** — um CSV com dados de vendas ou estoque (pode ser um dataset público pequeno, ou gerado por você mesmo com dados fictícios, mas realistas: pelo menos 100-200 linhas, com alguns dados propositalmente "sujos" — nulos, duplicados, tipo errado — pra você ter o que validar de verdade).
2. **Escrever um script Python de ETL completo**: Extract (lê o CSV), Transform (limpeza + pelo menos uma agregação/cálculo derivado + validação explícita que rejeita ou sinaliza linhas ruins), Load (grava o resultado limpo numa tabela Postgres).
3. **Instalar o Power BI Desktop** (gratuito) e conectar na mesma base Postgres onde você carregou os dados.
4. **Construir um dashboard simples** com pelo menos: um gráfico, uma tabela e um KPI/card numérico, a partir dos dados que você mesmo carregou.
5. **Fechar com uma reflexão curta**: qual validação de qualidade de dados você implementou no passo de Transform, e por que ela pegaria um problema real (dê um exemplo concreto do dado sujo que você usou e como a validação reage a ele).

## Requisitos

- Documento escrito (Markdown) relatando o que você fez, com o script Python anexado/linkado e prints ou descrição do dashboard do Power BI.
- A validação de qualidade de dados do passo 2 precisa ser código real que roda (rejeita, corrige ou sinaliza), não um comentário dizendo "aqui eu validaria".
- A reflexão do passo 5 usa um exemplo concreto dos seus próprios dados, não uma resposta genérica.

## Critérios de aceite

- [ ] Script Python executa um E-T-L completo: extrai do CSV, transforma (limpeza + pelo menos uma agregação/cálculo derivado), carrega no Postgres.
- [ ] Existe validação de qualidade de dados real no passo de transformação (não é só "roda sem erro").
- [ ] Power BI Desktop instalado, conectado à mesma base, com pelo menos 2 visualizações reais a partir dos dados carregados.
- [ ] Documento explica, com suas palavras, a diferença entre ETL e ELT.
- [ ] Reflexão final usa um exemplo concreto de dado sujo e como a validação reage a ele.

## Execução

Sem assistência de IA — apenas autocomplete padrão do editor. Quando terminar, volte e peça revisão (skill `professor-mentor`, modo Revisão). Só depois de concluir esta fase retome a Fase 2.
