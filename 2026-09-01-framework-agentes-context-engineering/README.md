# Desenho: escolha de framework de agentes + estratégia de Context Engineering

**Nível:** Especialista (staff/principal/Tech Lead)

## Motivação

Engenharia de IA agêntica tem hoje um punhado de frameworks de agentes consolidados (LangGraph, CrewAI, AutoGen, Claude SDK) e duas disciplinas que ganharam nome próprio: "Context Engineering" e "Harness Engineering". São dois gaps reais e específicos: você tem domínio profundo do *padrão* de orquestração multiagente (via Agno, em produção), mas nunca usou esses frameworks especificamente nomeados nem formalizou sua prática de gestão de contexto sob esses termos.

## Contexto

Você está montando uma proposta de arquitetura para uma plataforma de agentes de IA voltada à aceleração do ciclo de desenvolvimento e testes de software. A plataforma precisa: orquestrar múltiplos agentes especializados, manter sessões de contexto de longa duração sem estourar a janela do modelo, e expor ferramentas via protocolo MCP para os agentes consumirem.

Você não vai escrever código neste desafio — o entregável é um **documento de decisão de arquitetura**, pronto para ser defendido numa revisão técnica.

## Objetivo

Produzir um documento (Markdown) que cubra:

1. **Comparação de frameworks** — Agno (o que você já usa) vs. pelo menos **dois** destes frameworks (LangGraph, CrewAI, AutoGen, Claude SDK). Pesquise a documentação oficial de cada um antes de responder — não é para adivinhar ou generalizar. Compare em pelo menos 3 eixos concretos: por exemplo, modelo de orquestração (grafo de estados vs. papéis vs. handoffs), como cada um trata memória/contexto nativamente, e maturidade de integração com MCP.
2. **Decisão e justificativa** — qual framework você escolheria para este cenário específico, e por quê — considerando não só capacidade técnica, mas curva de adoção pro time e pra você mesmo.
3. **Estratégia de Context Engineering** — como você manteria uma sessão de longa duração sem estourar a janela de contexto do modelo? Nomeie técnicas concretas (ex.: sumarização incremental, memória externa/RAG, truncamento seletivo, hierarquia de contexto) e em que momento cada uma entra.
4. **Harness de orquestração, rastreabilidade e governança** — como você desenharia o "harness" que envolve os agentes: logging estruturado por decisão do agente, como você audita "por que o agente fez X", como você limita ações destrutivas de um agente autônomo.
5. **Onde MCP entra vs. onde não entra** — critério explícito pra decidir quando expor algo como ferramenta MCP vs. quando é melhor deixar dentro do próprio agente ou de um pipeline de RAG.

## Requisitos

- Documento escrito (Markdown), não implementação.
- A comparação de frameworks (item 1) exige pesquisa real de pelo menos 2 frameworks — cite o que você leu (documentação oficial, não resumos de terceiros). Não é aceitável comparação genérica de marketing.
- A estratégia de Context Engineering (item 3) precisa nomear pelo menos 2 técnicas concretas, cada uma com critério de quando se aplica.

## Critérios de aceite

- [ ] Pelo menos 2 dos frameworks listados foram pesquisados e comparados com Agno em pelo menos 3 eixos concretos.
- [ ] A decisão de framework tem justificativa que vai além de "é mais popular" — trade-offs reais e específicos ao cenário.
- [ ] A estratégia de Context Engineering nomeia técnicas concretas com critério explícito de quando usar cada uma.
- [ ] O harness de governança define pelo menos um mecanismo concreto de auditoria/rastreabilidade e um de limite de ação autônoma.
- [ ] O critério de MCP vs. não-MCP é explícito e aplicável a um caso real, não vago.

## Execução

Sem assistência de IA — apenas autocomplete padrão do editor (pesquisa em documentação oficial dos frameworks é permitida e esperada). Quando terminar, volte e peça revisão (skill `professor-mentor`, modo Revisão).
