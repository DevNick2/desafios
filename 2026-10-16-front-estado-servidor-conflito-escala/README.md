# Front-end sob carga: estado de servidor, conflito de edição e lista grande

**Nível:** Avançado (pl↔sr)

---

## Motivação

Boa parte do que derruba uma interface de verdade não é CSS nem componente: é **estado**. Quem é dono do dado — o servidor ou a tela? O que acontece quando duas pessoas editam o mesmo registro? Como mostrar 50 mil linhas sem travar o navegador? E como manter o filtro ao recarregar a página?

Essas quatro perguntas aparecem juntas em qualquer painel administrativo sério, e nenhuma se resolve com framework — todas exigem decisão. Este desafio existe para exercitar o front-end no ponto em que ele deixa de ser montagem de componente e vira arquitetura.

---

## Pré-requisito

Antes do desafio, construa a API que a interface vai consumir. **Este código é seu.**

### Domínio: solicitações de titulares de dados

Um sistema recebe pedidos de pessoas sobre os próprios dados pessoais, e cada pedido tem **prazo legal**.

### `GET /requests`

Aceita `page`, `page_size` (máx. 200), `status`, `request_type`, `assignee`, `q` (busca por nome ou e-mail) e `sort` (`due_at`, `received_at`, `subject_name`, com `-` para descendente). Devolve `{ items, total, page, page_size }`.

### `PATCH /requests/{id}`

Recebe os campos a alterar **mais `version`**. Se a `version` enviada for diferente da atual, responde **409** com o registro atual no corpo. Em caso de sucesso, incrementa `version` e devolve o registro.

### Campos

| Campo | Tipo |
|---|---|
| `id` | uuid |
| `subject_name` | string |
| `subject_email` | string |
| `request_type` | `access` · `deletion` · `correction` · `portability` |
| `status` | `received` · `in_review` · `awaiting_subject` · `completed` · `rejected` |
| `received_at` | timestamp |
| `paused_days` | inteiro |
| `assignee` | string ou nulo |
| `notes` | texto |
| `version` | inteiro |

### Regra de negócio — prazo e risco

**1. Prazo base**, em dias corridos a partir de `received_at`:

| `request_type` | Prazo |
|---|---|
| `access`, `portability` | **15 dias** |
| `deletion`, `correction` | **30 dias** |

**2. O relógio pausa.** Enquanto `status` é `awaiting_subject`, o prazo não corre. `due_at = received_at + prazo_base + paused_days`.

**3. Classificação de risco** (calculada, nunca armazenada):

| Condição | `sla_risk` |
|---|---|
| faltam mais de 5 dias para `due_at` | `on_time` |
| faltam de 0 a 5 dias | `at_risk` |
| `due_at` já passou e `status` não é `completed` nem `rejected` | `overdue` |
| `status` é `completed` ou `rejected` | `closed` |

**4. Transições válidas.** `received` → `in_review` → (`awaiting_subject` ↔ `in_review`) → `completed` ou `rejected`. Qualquer outra transição responde **422** com `INVALID_TRANSITION`.

**5. Regras de campo na transição:**
- `in_review` exige `assignee` preenchido → senão **422** `ASSIGNEE_REQUIRED`
- `completed` e `rejected` exigem `notes` com pelo menos 20 caracteres → senão **422** `NOTES_REQUIRED`

### Dataset

**Peça para a IA gerar** — é dado de teste e segue esta especificação à risca:

- **50.000 solicitações**, `received_at` espalhado nos últimos 18 meses.
- Distribuição de `request_type`: access 45%, deletion 30%, correction 15%, portability 10%.
- Distribuição de `status`: received 20%, in_review 35%, awaiting_subject 10%, completed 30%, rejected 5%.
- **12 valores distintos** de `assignee`, mais os nulos dos `received`.
- Casos de borda obrigatórios:
  - ~8% com `due_at` no passado e status aberto (exercita `overdue`);
  - ~6% caindo na janela de 0 a 5 dias (exercita `at_risk`);
  - 40 registros com `paused_days` entre 10 e 60, para a pausa importar;
  - 30 registros com **o mesmo `received_at` ao segundo**, para a ordenação precisar de desempate estável;
  - 15 com `subject_name` de 120+ caracteres e 15 com acentuação e caracteres especiais;
  - 200 com `notes` longo (2.000+ caracteres).

---

## Ambiente de execução

Tudo local, sem conta paga.

| Dependência | Como roda |
|---|---|
| API | Node.js local (seu código) |
| Banco | Postgres em container, ou SQLite se preferir |
| Front | **Vue 3** com Vite |
| Medição de performance | DevTools do navegador (Performance) e `performance.now()` |
| Gerador do dataset | **Apoio** — a IA pode construir seguindo a especificação |

---

## Contexto

A tela atual lista as solicitações, mas: o filtro se perde ao recarregar, a lista trava acima de alguns milhares de linhas, duas pessoas editando o mesmo registro fazem a última escrita vencer em silêncio, e o usuário descobre que errou a transição só depois de salvar.

---

## Objetivo

Construir a interface de triagem dessas solicitações de forma que **o estado seja explícito, o conflito seja visível e a escala seja medida**.

---

## Requisitos

**1. A URL é a fonte da verdade.** Filtro, busca, ordenação e página vivem na query string. Recarregar reproduz a tela, e o link colado para outra pessoa abre exatamente a mesma visão. Botão voltar do navegador funciona.

**2. Estado de servidor separado do estado de UI.** Escreva, no README da sua entrega, **o que você classificou como cada um e por quê**. A lista, o registro aberto e o total são estado de servidor; o que está selecionado, o que está expandido e o rascunho do formulário não são. Essa fronteira é a decisão central do desafio.

**3. Cache com revalidação sem flicker.** Ao voltar para um filtro já visitado, mostrar o dado em cache imediatamente e revalidar em segundo plano. A tela **não pode piscar** nem voltar para o estado de carregamento quando já há dado. Invalidação explícita após uma edição bem-sucedida.

**4. Lista grande.** Com `page_size` alto (as 50 mil disponíveis), a rolagem precisa ser fluida. Virtualize ou pagine — a escolha é sua, mas **justifique com número**: meça o tempo de render e a taxa de quadros durante a rolagem, antes e depois, e registre os dois.

**5. Edição otimista com conflito resolvido pelo usuário.** Ao salvar, atualize a tela antes da resposta. Em **409**, não basta avisar: mostre **o que mudou** entre a sua versão e a do servidor, campo a campo, e ofereça as três saídas — manter o meu, usar o do servidor, ou escolher por campo. Em **422**, mostre o erro no campo certo, não num alerta genérico.

**6. Validação no cliente que espelha a do servidor, sem duplicar a verdade.** Transição inválida e campo obrigatório devem ser barrados antes do request — mas o servidor continua sendo quem decide, e a resposta dele precisa ser tratada mesmo quando o cliente achou que estava tudo certo. Explique como você evitou que as duas regras divergissem com o tempo.

**7. Acessibilidade de teclado.** Navegar a lista e abrir o editor sem mouse. O foco vai para o editor ao abrir e **volta para a linha de origem** ao fechar. Mudança de status é anunciada por região viva (`aria-live`).

**8. Testes.** No mínimo: o fluxo de conflito 409 (incluindo a resolução campo a campo) e uma transição inválida barrada pelo servidor apesar do cliente.

---

## Critérios de aceite

- [ ] Recarregar a página com filtro, busca, ordenação e página aplicados reproduz a tela idêntica; voltar/avançar do navegador funciona.
- [ ] Voltar a um filtro já visitado mostra dado imediatamente, sem estado de carregamento, e revalida em segundo plano.
- [ ] Após uma edição, a lista reflete a mudança sem recarregar a página inteira.
- [ ] Tabela comparativa de **tempo de render e taxa de quadros** na rolagem, antes e depois da sua estratégia de escala, com o método de medição descrito.
- [ ] Conflito 409 mostra a diferença campo a campo e oferece as três resoluções; há teste cobrindo isso.
- [ ] Erro 422 aparece no campo correspondente.
- [ ] Documento escrito separando estado de servidor de estado de UI, com a justificativa.
- [ ] Explicação escrita de como cliente e servidor mantêm a mesma regra sem duplicar a fonte da verdade.
- [ ] Lista e editor navegáveis só pelo teclado, com foco retornando à origem ao fechar.
- [ ] Desempate estável na ordenação: os 30 registros com `received_at` idêntico aparecem sempre na mesma ordem entre recarregamentos.

---

## Trade-offs para decidir (não há resposta certa, há resposta defendida)

- Virtualizar mantém o filtro de 50 mil numa tela só e complica acessibilidade e busca do navegador. Paginar é simples e esconde o todo. Qual problema do usuário você escolheu resolver?
- Edição otimista deixa a tela rápida e cria o momento em que o que está na tela é mentira. Onde está o seu limite para isso?
- Validar no cliente dá retorno imediato e duplica regra. Como você escolheu evitar a divergência: contrato gerado, regra compartilhada, ou aceitar a duplicação com teste que a vigia?
- Cache por rota é simples de invalidar; cache global é eficiente e difícil de raciocinar. Qual você escolheu, e o que perdeu com isso?

---

> **Execução sem IA — apenas autocomplete padrão do editor.** Vale para o pré-requisito (a API e a regra de prazo) e para todo o desafio: roteamento de estado, cache, virtualização, resolução de conflito, acessibilidade e as justificativas escritas são seus. A IA pode construir apenas o **gerador do dataset**, e responder dúvidas conceituais sem entregar a solução. O produto final é o tipo de material que se defende numa revisão técnica de arquitetura: números medidos e decisões justificadas.
