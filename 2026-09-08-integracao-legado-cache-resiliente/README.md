# Desafio — Integração Resiliente com Sistema Legado + Cache com Invalidação Ativa

> Nível: **Avançado** (pl↔sr)
> Aplicado a um caso real de um dos seus próprios repositórios (uma API Python já em produção/desenvolvimento sua — escolha uma que tenha um endpoint de leitura e onde faça sentido introduzir uma dependência externa lenta).
> Execução sem IA — apenas autocomplete padrão do editor.

---

## Motivação

Gap identificado num processo seletivo real (detalhes da empresa omitidos de propósito): você sabe **explicar** circuit breaker, anti-corruption layer e proteção contra cache stampede — já aplicou o padrão Strangler Fig e circuit breaker numa migração real —, mas não há nos seus repositórios nenhuma **implementação hands-on** de integração com um sistema externo lento/instável nem de cache com invalidação ativa (hoje o que existe é conhecimento aplicado uma vez em produção, não um caso de estudo reproduzível e testável). Este desafio fecha essa lacuna combinando os dois problemas num cenário só, porque na prática eles aparecem juntos: proteger um consumidor de uma dependência lenta é exatamente o motivo mais comum para introduzir cache.

## Contexto

Você tem uma API Python já existente (escolha uma sua, ex. `api-monettra` ou outra API real que já tenha um endpoint de leitura). Essa API precisa expor um endpoint que depende de um **sistema legado externo simulado**: lento (latência alta, ~3-5s) e instável (falha uma fração perceptível das chamadas). O endpoint é consultado com alta frequência, e os dados do legado mudam pouco (ex.: a cada 15 minutos).

Você **não vai integrar com um SOAP real** — vai simular o comportamento do legado localmente (um serviço fake com `sleep` proposital e falha aleatória configurável, rodando em processo separado ou como stub HTTP), para poder testar os cenários de falha de forma controlada e repetível.

## Objetivo

Implementar, no código (não é documento de arquitetura — este desafio é hands-on), uma camada entre a sua API e o legado simulado que:

1. Isola a API do legado (nenhum consumidor da sua API espera 3-5s nem recebe erro por instabilidade do legado).
2. Serve dados do legado via cache, com invalidação ativa (não só TTL passivo).
3. Se comporta corretamente sob falha (o legado cai, mas sua API continua respondendo com o último dado bom conhecido, de forma explícita — não silenciosa).

## Requisitos

1. **Anti-corruption layer / adapter** — um módulo isolado responsável por toda comunicação com o legado simulado, com um contrato próprio (não vaza detalhes do legado para o resto da aplicação).
2. **Circuit breaker** — depois de N falhas consecutivas (parametrizável), o adapter para de chamar o legado por um período (open state), volta a tentar de forma controlada (half-open), e registra essa transição de forma observável (log estruturado ou métrica).
3. **Retry com backoff** — para falhas transitórias, com limite de tentativas e backoff exponencial; timeout explícito abaixo do tempo médio de resposta do legado.
4. **Cache com invalidação ativa** — cache-aside (ex. Redis, ou uma implementação in-memory com TTL se preferir simplificar a infra) onde a invalidação não depende só do TTL: simule um evento de atualização (ex. um endpoint interno ou job que dispara a invalidação) e mostre que o cache reflete o dado novo imediatamente após esse evento.
5. **Proteção contra stampede** — quando o cache expira/é invalidado sob carga concorrente, apenas uma requisição deve de fato chamar o legado; as demais aguardam ou recebem o dado servido por essa primeira chamada (lock/single-flight).
6. **Fallback explícito em falha** — quando o circuit breaker está aberto e não há cache válido, a resposta deve deixar claro (status code e corpo) que é um fallback ou indisponibilidade parcial, nunca um erro genérico 500 nem um dado silenciosamente desatualizado sem sinalização.
7. **Testes automatizados** cobrindo: circuit breaker abrindo e fechando, cache servindo dado correto após invalidação, e o comportamento de stampede sob chamadas concorrentes (pode usar testes com concorrência simulada, não precisa de carga real).

## Critérios de aceite

- Rodando o legado simulado com falha configurada em 100%, a API não trava nem demora 3-5s para responder — responde rápido com fallback ou erro claro.
- Depois de disparar o evento de invalidação, uma nova chamada ao endpoint reflete o dado atualizado sem esperar o TTL expirar.
- Um teste com múltiplas chamadas concorrentes após invalidação comprova que o legado simulado foi chamado uma única vez (não N vezes).
- O circuit breaker tem estado observável (log ou métrica) nas transições closed → open → half-open → closed.
- Nenhum detalhe de implementação do legado (formato de erro, latência) vaza para fora do adapter — o resto da API só conhece o contrato do adapter.
