# Desenho: operação Kubernetes + arquitetura orientada a eventos (cenário Onebrain+Stoom) — Fase 2 de 2

**Nível:** Especialista (staff/principal/Tech Lead)

**Pré-requisito (Fase 1):** [desafios/2026-09-01-onebrain-stoom-fundamentos-docker-k8s-eventos](../2026-09-01-onebrain-stoom-fundamentos-docker-k8s-eventos/README.md) — conclua antes de começar esta. Você ainda não tem experiência prática com Kubernetes; a Fase 1 constrói essa base (container, cluster local, objetos básicos, scaling manual) antes deste desenho de nível sênior/entrevista.

## Motivação

Vaga real e ativa (Tech Lead Node.js/React, grupo Onebrain+Stoom — análise completa em [`perfil_profissional/entrevistas/onebrain-stoom-tech-lead-nodejs-react.md`](../../perfil_profissional/entrevistas/onebrain-stoom-tech-lead-nodejs-react.md)). As perguntas técnicas prováveis da entrevista (seção 2 daquele documento) cruzam dois eixos:

1. **Kubernetes** — "Já operou Kubernetes em produção? Descreva um cenário de troubleshooting de scaling ou de uma falha de deploy." Este é um **gap real e não documentado**: a seção "5. Feitos no trabalho atual" daquele mesmo documento não tem nenhuma entrada de evidência para Kubernetes, ao contrário de arquitetura orientada a eventos (que você já tem — ver ponto 2).
2. **Arquitetura orientada a eventos (SQS/SNS)** — aqui você já tem evidência real e forte (a migração do monólito para um serviço event-driven em Python publicando em SNS, com padrão Strangler Fig). O desafio não é aprender o conceito, é **integrar** essa experiência com a operação em Kubernetes — que é exatamente o tipo de pergunta de Tech Lead sênior ("como esses serviços rodariam em produção, escalando, sob falha?").

## Contexto

Você está na entrevista técnica final para essa vaga. O entrevistador pega o case real que você já descreveu (o serviço event-driven que consome de um tópico SNS, com um proxy Strangler Fig na frente) e pergunta: "beleza, isso já roda em produção — mas como você desenharia a operação disso em Kubernetes, e o que você faria se esse serviço começasse a falhar sob carga às 9h da manhã (exatamente o horário da rotina agendada que você mencionou)?"

Você não vai escrever YAML de produção nem código neste desafio — o entregável é um **documento de decisão técnica**, pronto para ser defendido em voz alta numa entrevista.

## Objetivo

Produzir um documento (Markdown) que cubra:

1. **Desenho do workload em Kubernetes** — como o serviço consumidor (o que processa a fila/tópico SNS→SQS) seria deployado: Deployment vs. Job/CronJob, estratégia de scaling (HPA baseado em quê — CPU não faz sentido para um consumidor de fila; qual métrica você usaria?), e por que essa escolha.
2. **Cenário de troubleshooting de scaling** — a pergunta literal da entrevista. Descreva um cenário concreto de falha (ex.: fila SQS acumulando, pods não escalando, ou escalando mas travando) e o passo a passo de diagnóstico: o que você olha primeiro, que métricas/logs, que hipóteses descarta e em que ordem.
3. **Boas práticas de segurança em imagem Docker multi-stage** — a segunda pergunta literal da entrevista. Aplique ao serviço Python do case real: o que entra em cada stage, o que nunca vai pra imagem final, e por quê.
4. **Circuit breaker e auto-scaling juntos** — você já mencionou circuit breaker e reforço de auto-scaling/load balancer como mitigação no case real. Neste desenho, explicite como essas duas coisas interagem especificamente em Kubernetes (ex.: um pod que abre circuito não deveria necessariamente ser matado por liveness probe — como você evita essa armadilha?).
5. **Resposta de entrevista em 30 segundos** — feche com uma versão falada, curta, de como você contaria essa história inteira (do incidente ao redesenho) numa pergunta comportamental tipo "me dê um exemplo de decisão de arquitetura sob pressão".

## Requisitos

- Documento escrito (Markdown), não implementação.
- O cenário de troubleshooting (item 2) precisa ser específico o bastante para ser contado como uma história real numa entrevista — não "eu olharia os logs", mas o quê, onde, em que ordem.
- A escolha de métrica de HPA (item 1) precisa vir com o porquê de CPU/memória não servirem para esse tipo de workload.
- O fechamento (item 5) tem limite real: precisa caber em ~30 segundos falados (regra prática: ~75-90 palavras).

## Critérios de aceite

- [ ] O desenho do workload nomeia explicitamente a métrica de scaling e justifica por que não é CPU/memória padrão.
- [ ] O cenário de troubleshooting tem passos ordenados e específicos (ferramentas, métricas, hipóteses), não genéricos.
- [ ] A resposta sobre Docker multi-stage é aplicada ao serviço Python do case real, não uma explicação genérica do conceito.
- [ ] A interação circuit breaker + liveness probe está explicitamente resolvida (não só mencionada).
- [ ] O fechamento de 30 segundos existe e respeita o limite de tamanho.

## Execução

Sem assistência de IA — apenas autocomplete padrão do editor. Quando terminar, volte e peça revisão (skill `professor-mentor`, modo Revisão).
