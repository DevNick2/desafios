# Desenho de arquitetura: migração de ERP com pipeline de ETL e qualidade de dados — Fase 2 de 2

**Nível:** Especialista (staff/principal/Tech Lead)

**Pré-requisito (Fase 1):** [desafios/2026-09-01-fundamentos-etl-powerbi](../2026-09-01-fundamentos-etl-powerbi/README.md) — conclua antes de retomar esta. Você ainda não tem experiência prática com ETL nem Power BI; a Fase 1 constrói essa base (pipeline ETL real, dashboard em Power BI) antes deste desenho de nível sênior.

## Motivação

Trocar de ERP é um dos projetos mais arriscados que um time técnico pode liderar: envolve migrar dados legados, montar processos de ETL, "garantir qualidade dos dados desde a origem" e manter relatórios de BI confiáveis durante a transição. Nenhum desses três pontos (ETL, ferramentas de BI, migração de sistemas legados de dados) tem hoje um caso prático seu — é um gap real, não hipotético.

## Contexto

Você é o Tech Lead recém-contratado (papel hipotético). A empresa vai trocar de ERP nos próximos 9 meses. O ERP atual alimenta faturamento, estoque e relatórios financeiros usados pela diretoria em planilhas Excel manuais. Ninguém confia 100% nos números hoje — já houve casos de estoque divergente entre o sistema e a contagem física, e a diretoria quer que o novo ERP "resolva isso de uma vez".

Você não vai escrever código de produção neste desafio — o entregável é uma **decisão de arquitetura documentada**, como se fosse levar essa proposta para o board e para o time.

## Objetivo

Produzir um documento de decisão de arquitetura (ADR ou formato equivalente, sua escolha) que cubra:

1. **Estratégia de migração** entre os dois ERPs — big bang vs. incremental/paralelo, e por quê, considerando o risco de dado errado já existente hoje.
2. **Pipeline de ETL** — desenho de alto nível (extração do ERP antigo, transformação/validação, carga no novo), e onde a validação de qualidade de dados entra no fluxo (não é uma etapa cosmética — é onde a divergência de estoque teria sido pega antes de virar problema de diretoria).
3. **Build vs. buy** para a camada de ETL/BI — script Python custom vs. ferramenta (ex: Airflow, ferramenta de BI com ETL embutido) — com um trade-off explícito de custo, tempo de implementação e manutenção a longo prazo.
4. **Comunicação do risco para stakeholders não técnicos** — como você explicaria pra diretoria, em uma frase, por que a migração não pode ser "big bang" no fim de semana (se essa for sua recomendação), sem soar como desculpa técnica.

## Requisitos

- Documento escrito (Markdown), não uma implementação.
- Cada decisão precisa vir com o trade-off considerado e descartado — não basta apontar a solução escolhida.
- Pelo menos uma seção deve endereçar como você mede "qualidade de dados desde a origem" de forma concreta (não é aceitável responder só "com testes" — que testes, em que ponto do pipeline, contra o quê).

## Critérios de aceite

- [ ] A estratégia de migração está justificada por risco, não só por preferência técnica.
- [ ] O desenho do pipeline de ETL nomeia explicitamente onde e como a validação de dados acontece.
- [ ] A decisão de build vs. buy tem pelo menos dois trade-offs concretos (não genéricos) a favor e contra.
- [ ] Existe uma explicação de risco em linguagem de negócio, sem jargão técnico, pronta para ser dita em voz alta numa reunião com a diretoria.

## Execução

Sem assistência de IA — apenas autocomplete padrão do editor. Quando terminar, volte e peça revisão (skill `professor-mentor`, modo Revisão).
