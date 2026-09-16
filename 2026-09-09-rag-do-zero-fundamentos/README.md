# Desafio — RAG do Zero: Ingestão, Chunking, Indexação e Busca

> Nível: **Iniciante**
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. **Regra extra deste desafio:** não use nenhum framework que abstraia RAG (nada de LangChain, LlamaIndex, Agno, etc.) — o objetivo é você mesmo tomar cada decisão (chunking, indexação, busca) na mão, sem um framework decidindo por você.

---

## Motivação

Gap confirmado em 2026-09-09, prioridade alta: você já usa recuperação de contexto em produção no Orchestra, mas via abstração do framework Agno — nunca tomou pessoalmente as decisões de arquitetura de um pipeline de RAG (tamanho de chunk, estratégia de indexação, forma de busca). Isso apareceu como gap real em pelo menos 3 processos seletivos ativos, incluindo a primeira pergunta de uma etapa de entrevista por IA. Este desafio existe para você conseguir responder essa pergunta com uma experiência de verdade, não emprestada de um framework.

## Pré-requisito

Escreva, dentro desta pasta, um pequeno corpus de **6 documentos de texto** (`.md` ou `.txt`, escritos por você — pode ser sobre um tema fictício de "manual interno de engenharia" ou qualquer domínio que você conheça bem), 300-600 palavras cada:

1. Política de deploy
2. Processo de code review
3. Política de férias
4. Guia de onboarding técnico
5. Política de segurança de dados
6. Processo de incidentes/on-call

**Requisito deliberado:** pelo menos 2 pares de documentos precisam ter alguma sobreposição de vocabulário (ex: "aprovação obrigatória" aparecendo tanto na política de deploy quanto na de segurança de dados, para contextos diferentes) — isso é o que torna a busca não-trivial (busca por palavra-chave simples erraria o documento certo).

Escreva também um **dataset de validação**: 8 perguntas em inglês nos campos de código (`question`, `expected_source_doc`) — cada pergunta deve ter uma resposta clara em exatamente um dos 6 documentos. Ex: `{"question": "How many vacation days does an employee get per year?", "expected_source_doc": "ferias.md"}`.

## Ambiente de execução

| Dependência | Como roda |
|---|---|
| Embeddings | `sentence-transformers` local ou modelo de embedding no **Ollama** (API paga como alternativa opcional) |
| LLM para gerar a resposta | **Ollama** com um modelo pequeno (ex.: 3–8B) — sem GPU roda devagar, mas roda |
| Índice | Em memória ou arquivo local, construído por você (é parte do exercício) |
| Conta / custo | Nenhum |

## Objetivo

Construir, do zero (sem framework de RAG), um pipeline completo: ingestão → chunking → embeddings → indexação → busca → geração de resposta final com um LLM.

## Requisitos

1. **Ingestão** — script que lê os 6 documentos do pré-requisito.
2. **Chunking próprio** — implemente sua própria função de chunking (por tamanho fixo com overlap, ou por parágrafo/seção — sua escolha, mas justificada por escrito). Nomeie os parâmetros em inglês (`chunk_size`, `chunk_overlap`).
3. **Embeddings** — gere vetores para cada chunk usando uma API de embeddings (OpenAI, Cohere) ou um modelo local (sentence-transformers). Justifique a escolha.
4. **Indexação** — armazene os vetores (pode ser uma lista em memória com similaridade de cosseno calculada na mão, ou um vector DB leve tipo Chroma/FAISS local — sua escolha, justificada).
5. **Busca** — dada uma query, gere o embedding dela e recupere os top-k chunks mais similares (defina k e justifique).
6. **Geração** — passe os chunks recuperados + a pergunta para um LLM e gere a resposta final.
7. **Avaliação contra o dataset de validação** — rode as 8 perguntas do pré-requisito e meça: para cada uma, o chunk recuperado em top-1 (ou top-3) veio do `expected_source_doc` correto? Reporte a métrica (ex: 6/8 = 75%).
8. **Iteração documentada** — depois da primeira rodada de avaliação, ajuste pelo menos um parâmetro (chunk_size, k, ou estratégia de chunking) para tentar melhorar o resultado, e registre: o que mudou, e o resultado antes/depois. Isso é o "o que não funcionou de primeira e o que você mudou" que toda entrevista real pergunta.

## Critérios de aceite

- Pipeline roda ponta a ponta com um único comando, da pergunta em texto até a resposta final gerada pelo LLM.
- A métrica de avaliação contra as 8 perguntas do dataset de validação está calculada e reportada, não estimada de cabeça.
- Existe pelo menos uma iteração real documentada (parâmetro mudado + resultado antes/depois), não só a primeira tentativa.
- Documento final (README próprio desta implementação, dentro desta pasta) responde, com números e decisões reais do seu próprio pipeline, as mesmas 4 perguntas que caem em entrevista: como foi a ingestão, qual estratégia de chunking e por quê, como foi a indexação, como funciona busca+recuperação até a resposta final — e o que não funcionou de primeira.
- Nenhum framework de RAG (LangChain, LlamaIndex, Agno) foi usado — só chamadas diretas a API de embeddings/LLM e sua própria lógica de chunking/busca.
