# Desafio — Arquitetura de Gateway de LLM e Governança de Dados Sensíveis

> Nível: **Especialista** (staff/principal/Tech Lead)
> Formato: documento de decisão de arquitetura (ADR) — **sem código**.
> Execução sem IA — apenas autocomplete padrão do editor. Este desafio existe para ser pensado e escrito por você; qualquer apoio de IA aqui se limita a esclarecer conceitos, nunca a redigir a decisão.

---

## Motivação

Gap identificado num processo seletivo real (detalhes da empresa omitidos de propósito): um produto SaaS já tem várias funcionalidades de IA em produção (chatbot, transcrição, geração de conteúdo), construídas ao longo do tempo sem padronização entre provedores de LLM, sem processo formal de avaliação de qualidade, e operando sobre dados sensíveis regulados (dados de saúde, sob LGPD). Isso expõe quatro lacunas específicas de "Especialista": desenho de camada de orquestração multi-provider, tratamento de prompt como código com testes de regressão, observabilidade de custo/qualidade em produção, e governança de dados sensíveis num pipeline que passa por LLMs de terceiros.

## Contexto

Você assume a liderança técnica de IA de um produto com as seguintes características:

- 4 funcionalidades de IA já em produção, cada uma integrada diretamente com a API de um provedor de LLM diferente (sem camada de abstração comum).
- Uma das funcionalidades já teve incidente público de qualidade (mensagem automática disparada de forma indevida a usuários finais).
- O produto processa dados sensíveis de saúde de terceiros, sujeitos à LGPD.
- A empresa acabou de captar investimento com parte do aporte carimbada especificamente para evoluir a frente de IA — ou seja, há orçamento, mas também expectativa de retorno mensurável.
- Não existe hoje processo de avaliação automatizada de qualidade de prompt, nem observabilidade de custo por chamada de modelo.
- A liderança de produto/negócio não tem vocabulário técnico de IA — qualquer decisão de arquitetura que envolva risco ou custo precisa ser explicável em linguagem de negócio.

## Objetivo

Escrever um documento de decisão de arquitetura (ADR) que resolva, de forma integrada, os quatro problemas do contexto — sem propor reescrita das 4 funcionalidades existentes.

## Requisitos

O documento deve conter, no mínimo, estas seções:

1. **Camada de orquestração (LLM Gateway)** — desenho de uma camada comum entre as funcionalidades e os provedores de LLM: o que ela padroniza (logging, retry, fallback entre modelos, medição de custo/latência), como as 4 funcionalidades existentes migram para ela de forma incremental sem downtime, e critério explícito de quando vale abstrair vs. quando acoplamento direto a um provedor é aceitável.
2. **Prompt como código** — estratégia de versionamento de prompts, testes de regressão (golden set) e avaliação automatizada (determinística vs. LLM-as-judge), e como isso entra no pipeline de CI antes de qualquer deploy de prompt ou troca de modelo.
3. **Observabilidade e custo** — que métricas capturar por chamada de modelo (custo, latência, taxa de erro, taxa de fallback), e como isso vira um painel que a liderança de produto consegue interpretar sem vocabulário técnico.
4. **Governança de dados sensíveis (LGPD)** — como dados de saúde chegam ao LLM: contrato de não-retenção com o provedor, anonimização/pseudonimização antes do envio, ou modelo self-hosted — comparação explícita de trade-offs (custo, latência, risco de compliance) e recomendação justificada.
5. **Plano de migração incremental** — ordem de migração das 4 funcionalidades para a nova arquitetura, priorizada por risco (a que já teve incidente entra quando: primeiro, por urgência, ou por último, por estabilidade?).
6. **Métricas de sucesso em 3, 6 e 12 meses** — indicadores que provam que a mudança de arquitetura teve efeito, em termos que a liderança de negócio entenda.
7. **Riscos e trade-offs explícitos** — pelo menos 3 riscos da sua proposta, com mitigação, escritos em linguagem de negócio (não jargão técnico).

## Critérios de aceite

- O documento não presume tecnologia específica de provedor sem justificar a escolha (ex: "usar OpenAI" sem comparar alternativas não passa).
- A camada de orquestração é descrita em termos de contrato/interface, não de código.
- A estratégia de prompt-como-código descreve o que entra no CI e o que bloqueia um deploy — não só "ter testes".
- A seção de LGPD compara pelo menos duas abordagens (não escolhe a primeira ideia sem contraste) e justifica a recomendação com trade-off de custo/latência/risco.
- O plano de migração é incremental e explica como evita quebrar as funcionalidades já em produção.
- Nenhuma seção deixa uma decisão de peso (ex: self-hosted vs. API de terceiro) sem justificativa explícita.
