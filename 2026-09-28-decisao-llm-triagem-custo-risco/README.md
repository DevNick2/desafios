# Desafio — Decisão de negócio sobre triagem com LLM: custo, latência e risco

**Nível:** Especialista (staff/principal/Tech Lead)
**Proposto em:** 2026-09-28
**Formato:** documento de decisão, **sem código**.
**Fase 2 de 2.** Depende dos números medidos na Fase 1 ([triagem com LLM: onde usar, como medir, como falhar](../2026-09-28-triagem-llm-avaliacao-falhas/README.md)). Sem a Fase 1 concluída, este documento vira opinião e não decisão.

---

## Motivação

A Fase 1 produz evidência: acurácia por categoria, custo por mil chamados, latência, taxa de fallback, um incidente investigado. Evidência sozinha não decide nada. Alguém precisa transformar esses números numa recomendação que uma pessoa de negócio consiga aprovar, recusar ou negociar, sabendo o que está comprando e o que está arriscando.

É a habilidade que mais pesa numa liderança técnica de IA e a que menos se treina: explicar **por que** uma arquitetura faz sentido, **como** ela falha e **como** evoluir sem quebrar a operação, sem usar o nome de nenhum framework como argumento.

---

## Pré-requisito

Fase 1 concluída, com `eval/REPORT.md`, `DECISIONS.md` e `INCIDENT.md` prontos. Os números deste documento saem de lá. O cenário de negócio abaixo é o estado assumido e não exige código.

---

## Contexto

A empresa da `support-api` é um SaaS B2B com estes números:

- **18.000 chamados por mês**, com pico de 1.400 num único dia de fechamento de fatura.
- **14 pessoas no suporte**, com custo médio de **R$ 45 por hora**.
- Hoje, **38%** dos chamados são reclassificados manualmente. Cada reclassificação consome **3 minutos** de quem triou e atrasa a primeira resposta em **2 horas** em média.
- Um chamado que chega na fila errada e não é corrigido gera **12 minutos** de retrabalho e, se for de cliente `enterprise`, conta como violação de SLA contratual, com multa de **R$ 400 por ocorrência**.
- Um chamado de `security` que não chega ao `security-team` em até 1 hora é tratado como **incidente de segurança reportável**. Não tem valor em reais: tem risco jurídico e de reputação.
- A diretoria de operações (COO) pediu: *"vamos colocar IA em 100% da triagem no próximo mês?"*. A pessoa não tem vocabulário técnico de IA e quer uma resposta que caiba numa reunião de 30 minutos.

---

## Objetivo

Escrever `DECISION.md`: uma recomendação sobre **se**, **onde** e **como** colocar o LLM na triagem, fundamentada nos números da Fase 1 e compreensível por quem não é técnico.

---

## Requisitos

O documento tem estas sete seções, nesta ordem. Cada uma responde a uma pergunta e **cita pelo menos um número medido na Fase 1**:

1. **Precisa de LLM?** Em quais categorias o LLM paga o próprio custo e em quais a regra continua melhor. Recomendação por categoria, não uma decisão única para tudo.
2. **O que fica em código e o que fica com o modelo.** Quais decisões nunca serão delegadas ao modelo (prioridade, SLA, `security`) e por quê, explicado em termos de risco para o negócio.
3. **Como vamos saber se melhorou.** A métrica de sucesso em linguagem de negócio (ex.: reclassificações por mês, minutos economizados, multas evitadas), o critério de rollback e como o golden set cresce com os overrides humanos.
4. **O que acontece quando falhar.** Da falha técnica ao efeito no cliente: provedor fora do ar, lentidão, resposta inválida, troca silenciosa de modelo (use o `INCIDENT.md`). Deixe explícito que o pior caso volta a ser o sistema de hoje, e prove com dados da Fase 1.
5. **Estado, contexto e memória.** Por que a triagem não "lê a conversa inteira", o que isso economiza (em tokens e em R$) e qual o limite dessa escolha. Explique como para alguém que nunca ouviu falar em janela de contexto.
6. **Como vamos investigar problemas.** O que a operação vê quando algo sair errado, quem é acionado, e o que o trace permite responder em minutos que hoje leva dias.
7. **Custo, latência e risco.** A conta completa para 18.000 chamados/mês, **em cada variante da Fase 1 e na baseline**:
   - custo mensal de inferência;
   - horas de suporte economizadas (ou perdidas) em reclassificação e retrabalho, em R$;
   - multas de SLA `enterprise` esperadas;
   - latência adicionada na criação do chamado, e se ela importa;
   - risco de `security` mal roteado, por quantidade esperada por mês e não por percentual.

   Feche com **uma recomendação**: qual variante, para quais categorias, com qual plano de rollout (ex.: sombra → porcentagem → 100%) e quais números dispararão rollback em cada etapa.

Depois das sete seções, mais três partes:

8. **Resposta à pergunta da COO**, em até **150 palavras**, sem jargão. "Sim", "não" e "sim, mas" são aceitos, desde que o "mas" seja concreto.
9. **Versão falada:** cada uma das sete seções resumida em até **120 palavras**, para ser explicada em até 1 minuto numa reunião de decisão. Sem citar framework, biblioteca ou nome de modelo. Se a explicação precisar deles, ela ainda não está boa.
10. **O que eu não sei:** as premissas mais frágeis do documento (ex.: o golden set de 90 chamados representa a produção?) e o que você mediria antes de ir para 100%.

---

## Critérios de aceite

1. Todas as sete seções citam pelo menos um número tirado de `eval/REPORT.md`, `DECISIONS.md` ou `INCIDENT.md` da Fase 1.
2. A seção 7 fecha a conta mensal em R$ para cada variante e para a baseline, com as premissas visíveis. Qualquer pessoa consegue refazer a conta.
3. A recomendação não é "100% LLM" nem "0% LLM" sem justificativa por categoria.
4. O plano de rollout tem critério de rollback numérico em cada etapa.
5. A resposta à COO cabe em 150 palavras e não usa nenhum destes termos: token, prompt, embedding, LLM, fine-tuning, RAG, agente, framework.
6. A versão falada tem sete blocos de até 120 palavras cada, e você consegue falar cada um **em voz alta, sem ler, em até 1 minuto**. Grave pelo menos três e cronometre.
7. "O que eu não sei" lista pelo menos três premissas, cada uma com a medição que a confirmaria ou derrubaria.

---

## Execução

**Sem IA.** O documento é pensado e escrito por você, apenas com o autocomplete padrão do editor. Apoio de IA aqui se limita a esclarecer um conceito quando você pedir, nunca a redigir seção, conta ou recomendação.

Quando terminar, peça a revisão. Ela lê como a COO leria primeiro (seções 8 e 9) e só depois confere as contas.
