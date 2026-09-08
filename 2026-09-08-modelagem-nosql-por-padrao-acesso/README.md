# Desafio — Modelagem NoSQL Orientada a Padrão de Acesso

> Nível: **Avançado** (pl↔sr)
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito, não só o desafio em si.

---

## Motivação

Gap detectado de forma independente em três processos seletivos (detalhes das empresas omitidos de propósito): NoSQL (DynamoDB/MongoDB) aparece como requisito ou diferencial, mas seu perfil hoje não tem nenhum caso documentado de modelagem NoSQL — o instinto de modelagem que você pratica (e domina bem) é relacional/normalizado. O erro mais comum de quem migra desse instinto para NoSQL é copiar a estrutura de tabelas relacionais para "coleções"/"tabelas" NoSQL, perdendo o ganho real: em NoSQL você modela **a partir dos padrões de acesso**, não a partir das entidades.

## Pré-requisito

Construa, dentro desta pasta, uma pequena API (linguagem/framework livres, identificadores de código em inglês) com um sistema de tickets de suporte, relacional (Postgres ou SQLite), com duas tabelas: `tickets` e `messages`.

Implemente exatamente esta regra de negócio:

> Um ticket tem `priority = URGENT` se: o campo `subject` contém qualquer uma das palavras "error", "outage" ou "production" (case-insensitive) **OU** o usuário que abriu o ticket tem `plan = ENTERPRISE`. Caso contrário, `priority = NORMAL`.
> (Para referência, não precisa ser aplicado em código ainda: SLA de primeira resposta é 1h para `URGENT` e 24h para `NORMAL`.)

Endpoints mínimos: `POST /tickets`, `GET /tickets/{id}` (com suas mensagens), `POST /tickets/{id}/messages`.

**Dataset:** 10 usuários (`id`, `name`, `plan` — 2 com `ENTERPRISE`, 8 com `STANDARD`), 25 tickets distribuídos ao longo de um período de 2 semanas (`id`, `user_id`, `subject`, `status` — `OPEN`/`CLOSED`, `priority`, `created_at`) com assuntos variados: pelo menos 8 disparando `URGENT` por palavra-chave, pelo menos 3 disparando `URGENT` só por plano enterprise, o resto `NORMAL`. 60-80 mensagens no total (2-5 por ticket), campos `ticket_id`, `sent_at`, `sender_type` (`CUSTOMER`/`AGENT`), `body`, com timestamps realistas.

Construa isso com seu instinto normal de modelagem relacional — é exatamente esse ponto de partida que o desafio pede pra você repensar depois.

## Contexto

O sistema de tickets, em produção, tem 4 padrões de acesso dominantes (é a partir deles que você vai modelar a versão NoSQL, não a partir das duas tabelas acima):

1. Buscar um ticket específico com todas as suas mensagens, em ordem cronológica.
2. Listar todos os tickets de um usuário, mais recentes primeiro.
3. Listar todos os tickets `OPEN` com `priority = URGENT`, para a fila de atendimento prioritário.
4. Contar quantos tickets `OPEN` cada usuário tem (para um badge "N tickets abertos" na UI).

## Objetivo

Modelar e migrar esses dados para um armazenamento NoSQL (DynamoDB Local, LocalStack, ou MongoDB — sua escolha, com justificativa) desenhado **a partir dos 4 padrões de acesso acima**, com uma migração real dos dados do pré-requisito relacional para o novo armazenamento. Isto é hands-on — entregável é código funcionando, não um documento de arquitetura.

## Requisitos

1. **Análise de padrão de acesso por escrito, antes de modelar** — uma tabela curta: padrão → frequência estimada → como seria a query relacional equivalente → por que ela fica cara/estranha em relacional na escala (ex. join repetido, contagem sem índice).
2. **Modelagem justificada** — single-table design (DynamoDB) ou multi-coleção deliberada (Mongo), com a chave de partição/ordenação (ou índices) escolhidos explicitamente para servir os 4 padrões sem table scan.
3. **Script de migração** que lê do banco relacional do pré-requisito e escreve no novo armazenamento NoSQL.
4. **Pelo menos um índice secundário** (GSI no DynamoDB, índice composto no Mongo) justificado por um padrão de acesso específico — diga qual padrão ele resolve e por quê a modelagem primária não bastava.
5. **Nota de trade-off** — o que você ganhou (qual padrão ficou mais rápido/simples) e o que perdeu (qual operação ficou mais difícil — ex. consulta ad-hoc, join entre tickets de usuários diferentes, rigidez de schema) — amarrado a este dataset específico, não uma afirmação genérica sobre NoSQL.
6. **Testes** validando que cada um dos 4 padrões de acesso retorna o resultado correto contra o novo armazenamento.

## Critérios de aceite

- Os 4 padrões de acesso estão implementados e corretos contra o armazenamento NoSQL.
- Nenhum dos 4 padrões depende de varrer a tabela/coleção inteira.
- O script de migração roda e produz um dataset com as mesmas contagens do relacional original.
- A nota de trade-off é concreta e amarrada ao dataset/padrões deste desafio — não uma afirmação genérica de "NoSQL é mais rápido".
- A escolha entre DynamoDB e MongoDB (ou outro) está justificada, não é só a opção default.
