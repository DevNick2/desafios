# Multi-tenant: isolamento que se prova, não que se promete

**Nível:** Intermediário (jr↔pl)

---

## Motivação

Num SaaS com muitos clientes na mesma base, vazar um registro de um cliente para outro não é bug comum: é incidente de segurança, com cliente avisado e, dependendo do dado, autoridade notificada. E o jeito mais frequente de isso acontecer é banal — **alguém esqueceu um `WHERE tenant_id = ?`** numa query nova, meses depois de o sistema estar correto.

Por isso o objetivo aqui não é "filtrar por tenant", que é fácil. É construir o isolamento de um jeito que **a ausência do filtro falhe em vez de vazar**, e escrever o teste que prova isso continuar verdade no futuro.

---

## Pré-requisito

Antes do desafio, construa a API que será isolada. **Este código é seu.**

### Domínio: registros de fornecedores por empresa cliente

Cada empresa cliente (tenant) mantém sua própria lista de fornecedores avaliados.

### Endpoints

- `POST /suppliers` — cria
- `GET /suppliers` — lista com `page`, `page_size`, `status`, `q`
- `GET /suppliers/{id}` — detalhe
- `PATCH /suppliers/{id}` — atualiza
- `GET /suppliers/{id}/score` — devolve o score calculado

O tenant vem de um header `X-Tenant-Id`.

### Campos

| Campo | Tipo |
|---|---|
| `id` | uuid |
| `tenant_id` | uuid |
| `legal_name` | string |
| `tax_id` | string (14 dígitos) |
| `country` | string (ISO 2 letras) |
| `annual_revenue_brl` | decimal |
| `sector` | `industry` · `services` · `retail` · `technology` |
| `sanctions_hits` | inteiro |
| `last_review_at` | timestamp ou nulo |
| `status` | `pending` · `approved` · `blocked` |

### Regra de negócio — score de risco

`risk_score` é calculado na leitura, de 0 a 100, **quanto maior pior**:

1. **Base por setor:** industry 20 · services 15 · retail 10 · technology 5
2. **Porte:** `annual_revenue_brl` acima de R$ 50.000.000 soma **15**; entre R$ 5.000.000 e R$ 50.000.000 soma **8**; abaixo soma **0**
3. **País:** diferente de `BR` soma **12**
4. **Sanções:** cada `sanctions_hits` soma **25**, limitado a 50 no total
5. **Revisão vencida:** se `last_review_at` é nulo ou tem mais de 365 dias, soma **10**
6. Resultado limitado a 100.

**Faixa:** `low` até 30 · `medium` de 31 a 60 · `high` acima de 60.

**Regra de bloqueio:** `sanctions_hits > 0` **força** `status = blocked`, independentemente do score. Tentar mover para `approved` nesse caso responde **422** com `SANCTIONED_SUPPLIER`.

### Dataset

**Peça para a IA gerar** — é dado de teste:

- **6 tenants**, com volumes desiguais: 20.000, 8.000, 3.000, 900, 120 e **1** fornecedor.
- Casos de borda obrigatórios:
  - **o mesmo `tax_id` existindo em 3 tenants diferentes** — a unicidade é por tenant, não global;
  - 50 fornecedores com `sanctions_hits > 0`, espalhados em vários tenants;
  - 200 com `last_review_at` nulo e 300 com revisão vencida;
  - valores que caiam exatamente nas fronteiras: score 30, 31, 60 e 61;
  - receita exatamente em R$ 5.000.000 e R$ 50.000.000.
- O tenant com **1 registro** existe de propósito: é o que denuncia paginação ou agregação que ignora o filtro.

---

## Ambiente de execução

| Dependência | Como roda |
|---|---|
| API | Node.js ou Python local (seu código) |
| Banco | **Postgres** em container (o desafio usa recursos de RLS, opcionais) |
| Testes | Framework da sua stack |
| Gerador do dataset | **Apoio** — a IA pode construir |

---

## Contexto

A API funciona e filtra por tenant em todos os endpoints — porque hoje alguém lembrou de escrever o filtro em cada query. Nada no sistema impede que a próxima query nasça sem ele.

---

## Objetivo

Mover o isolamento de "disciplina de quem escreve a query" para "propriedade do sistema", e provar com teste que ele se mantém.

---

## Requisitos

**1. Escolha e justifique a estratégia de isolamento.** As candidatas: filtro na aplicação, **Row-Level Security do Postgres**, schema por tenant, ou banco por tenant. Escreva por que a sua escolha serve a este cenário — lembrando que os volumes vão de 1 a 20.000 registros por tenant, e que o número de tenants cresce.

**2. O caminho sem filtro tem que falhar.** Depois da sua mudança, uma query nova escrita **sem** mencionar tenant deve retornar vazio ou dar erro — nunca dados de outro tenant. Demonstre isso com um teste que executa uma consulta deliberadamente ingênua.

**3. Unicidade por tenant.** `tax_id` é único dentro do tenant e pode repetir entre tenants. Garanta isso no banco, não só na aplicação, e teste os dois lados: o duplicado barrado dentro do tenant e o mesmo valor aceito em outro.

**4. Tenant ausente ou inválido.** Requisição sem `X-Tenant-Id`, com tenant inexistente, ou com tenant ao qual o chamador não pertence: defina e implemente o comportamento, e **diga por que escolheu 400, 403 ou 404** — a escolha entre 403 e 404 vaza ou esconde a existência do tenant, e isso é decisão de segurança.

**5. Agregações e paginação.** `GET /suppliers` com contagem total e `GET /suppliers/{id}/score` precisam respeitar o isolamento. O tenant de 1 registro é o seu canário: se a contagem total dele vier maior que 1, há vazamento em agregação.

**6. Acesso cruzado por id.** Pedir `GET /suppliers/{id}` com o id de um fornecedor de **outro** tenant não pode devolver o registro. Teste explícito.

**7. Rastro.** Toda requisição registra o tenant no log estruturado. Sem isso, investigar um incidente de vazamento vira arqueologia.

---

## Critérios de aceite

- [ ] Documento curto com a estratégia escolhida e a justificativa, incluindo o que você descartou e por quê.
- [ ] Teste que roda uma query sem filtro de tenant e prova que **não** vazam dados.
- [ ] Teste do `tax_id` duplicado: barrado no mesmo tenant, aceito em tenant diferente, com a restrição no banco.
- [ ] Teste de acesso cruzado por id, para todos os endpoints que recebem `{id}`.
- [ ] Contagem total do tenant de 1 registro devolve exatamente 1.
- [ ] Comportamento definido e testado para tenant ausente, inexistente e não autorizado, com a escolha do código HTTP justificada.
- [ ] `risk_score` correto nas quatro fronteiras do dataset (30, 31, 60, 61) e na regra de sanção que força `blocked`.
- [ ] Log estruturado com `tenant_id` em toda requisição.

---

## Trade-offs para decidir

- RLS move a garantia para o banco e torna a depuração menos óbvia. Filtro na aplicação é transparente e depende de ninguém esquecer. O que você prefere explicar num incidente?
- Schema por tenant isola bem e multiplica migrações por 6, por 600, por 6.000. Onde está o ponto em que isso deixa de compensar?
- Responder 404 para um recurso de outro tenant esconde que ele existe; 403 admite. Qual dos dois você entrega a um atacante?

---

> **Execução sem IA — apenas autocomplete padrão do editor.** Vale para o pré-requisito (a API e a regra de score) e para o desafio: estratégia de isolamento, restrições, testes e justificativas são seus. A IA pode construir apenas o **gerador do dataset**, e responder dúvidas conceituais sem entregar a solução.
