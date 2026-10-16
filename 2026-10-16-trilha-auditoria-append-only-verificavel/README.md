# Trilha de auditoria: append-only que se verifica sozinha

**Nível:** Intermediário (jr↔pl)

---

## Motivação

Quase todo sistema tem uma tabela chamada `logs` ou `audit`. Quase nenhuma serve como prova, porque duas perguntas ficam sem resposta: **quem pode alterar essa tabela?** e **como alguém prova que ela não foi alterada?**

Se a resposta for "ninguém mexe porque combinamos que não mexe", a trilha não vale nada num momento de disputa — que é exatamente o único momento em que ela é consultada. Este desafio constrói a versão que vale: append-only de verdade, encadeada por hash, verificável por um terceiro, e com política de retenção que não contradiz a imutabilidade.

---

## Pré-requisito

Antes do desafio, construa a aplicação que gera os eventos. **Este código é seu.**

### Domínio: acesso a documentos sensíveis

Um sistema guarda documentos de acesso restrito. Toda leitura, download e mudança de permissão precisa deixar rastro.

### Endpoints

- `POST /documents` — cria documento (`title`, `classification`, `owner_id`)
- `GET /documents/{id}` — lê metadados
- `GET /documents/{id}/content` — lê o conteúdo (é isto que precisa de rastro forte)
- `POST /documents/{id}/grants` — concede acesso a um usuário (`user_id`, `level`)
- `DELETE /documents/{id}/grants/{user_id}` — revoga

### Campos de `documents`

`id`, `title`, `classification` (`public` · `internal` · `confidential` · `restricted`), `owner_id`, `created_at`

### Regra de negócio — quem pode ler

Níveis de concessão: `viewer` (lê metadados e conteúdo), `auditor` (lê metadados, **não lê conteúdo**), `manager` (tudo, e pode conceder).

| Classificação | Quem lê o conteúdo |
|---|---|
| `public` | qualquer usuário autenticado |
| `internal` | qualquer usuário autenticado |
| `confidential` | dono, ou concessão `viewer`/`manager` |
| `restricted` | dono, ou concessão `manager`; **`viewer` não basta** |

Acesso negado responde **403** — **e o 403 também gera evento de auditoria**, porque tentativa negada é o que mais interessa numa investigação.

Concessão em documento `restricted` exige que quem concede seja o **dono** (nem `manager` pode repassar) → senão **403** `GRANT_NOT_ALLOWED`.

### Dataset

**Peça para a IA gerar** — é dado de teste:

- **800 documentos**: 15% `public`, 40% `internal`, 30% `confidential`, 15% `restricted`.
- **120 usuários** e cerca de 2.500 concessões, distribuídas entre os três níveis.
- **40.000 eventos de acesso** simulados ao longo de 12 meses, incluindo:
  - ~6% de tentativas **negadas** (403), espalhadas entre as quatro classificações;
  - 200 acessos do mesmo usuário ao mesmo documento no mesmo minuto (rajada);
  - 50 eventos com `user_agent` e `ip` ausentes, para o esquema aguentar campo faltante;
  - 30 revogações seguidas de nova tentativa de leitura pelo usuário revogado.

---

## Ambiente de execução

| Dependência | Como roda |
|---|---|
| Aplicação | Node.js ou Python local |
| Banco | **Postgres** em container |
| Verificador | Script separado, na linguagem que quiser |
| Gerador do dataset | **Apoio** — a IA pode construir |

---

## Contexto

A tabela de auditoria existe e registra os acessos. Ela também aceita `UPDATE` e `DELETE` de quem tiver a credencial da aplicação, não tem como detectar remoção de uma linha do meio, e ninguém sabe dizer o que acontece com ela daqui a sete anos.

---

## Objetivo

Transformar essa tabela numa trilha que **resiste a alteração, detecta adulteração e tem política de retenção escrita**.

---

## Requisitos

**1. Append-only no banco, não no acordo.** Impeça `UPDATE` e `DELETE` na tabela de auditoria com mecanismo do próprio Postgres — trigger, revogação de privilégio, ou os dois. Demonstre com um teste que tenta alterar e falha. "A aplicação não faz isso" não é resposta aceita.

**2. Encadeamento por hash.** Cada evento guarda o hash do anterior, formando uma cadeia. Remover ou editar uma linha do meio tem que quebrar a verificação. Defina e documente **exatamente quais campos entram no hash** e em que ordem — se a serialização variar, a cadeia quebra sozinha e você vai perseguir um fantasma.

**3. Verificador independente.** Um script que percorre a trilha e responde **íntegra** ou **quebrada a partir do evento N**. Ele não compartilha código com a aplicação que escreve — um verificador que usa a mesma função de serialização do escritor não prova nada contra um escritor comprometido.

**4. Três cenários de adulteração, demonstrados.** Com o verificador rodando: (a) alterar o conteúdo de um evento; (b) remover um evento do meio; (c) inserir um evento forjado entre dois existentes. Nos três, o verificador precisa apontar onde quebrou. Documente os comandos.

**5. O que entra na trilha.** Leitura de conteúdo, concessão, revogação **e tentativa negada**. Cada evento registra ator, ação, alvo, resultado, timestamp e correlação. **Não registre o conteúdo do documento** — trilha de auditoria que copia o dado sensível duplica o problema que deveria vigiar.

**6. Rajada sem furo.** Os 200 acessos no mesmo minuto não podem gerar colisão de ordem nem buraco na cadeia. Se você escreve de forma concorrente, explique como garantiu a ordem — e se serializou, diga o custo disso.

**7. Retenção sem contradizer a imutabilidade.** Defina por quanto tempo a trilha vive e o que acontece depois. Expurgar o começo da cadeia quebra a verificação do que sobrou — **resolva isso explicitamente**: âncora periódica, selagem por período, ou segmentação. A política escrita vale tanto quanto o código.

**8. Consulta útil.** Responder, com índice adequado: "tudo que o usuário X fez nos últimos 90 dias" e "todos que acessaram o documento Y". Uma trilha que ninguém consegue consultar não é usada.

---

## Critérios de aceite

- [ ] Teste que tenta `UPDATE` e `DELETE` na tabela de auditoria e falha pelo mecanismo do banco.
- [ ] Documento especificando os campos do hash, a ordem e o formato de serialização.
- [ ] Verificador independente rodando e declarando a trilha íntegra nos 40.000 eventos.
- [ ] Os três cenários de adulteração demonstrados, com o verificador apontando o ponto de quebra e os comandos registrados.
- [ ] Tentativas negadas (403) presentes na trilha — verificável contando os ~6% do dataset.
- [ ] Nenhum conteúdo de documento dentro da trilha.
- [ ] Os 200 acessos da rajada aparecem todos, em ordem determinística, sem furo na cadeia.
- [ ] Política de retenção escrita, com a solução para o conflito entre expurgo e verificabilidade.
- [ ] As duas consultas respondendo com plano de execução usando índice, não varredura completa.

---

## Trade-offs para decidir

- Escrever a trilha na mesma transação da operação garante consistência e acopla a disponibilidade: se a auditoria cai, a operação cai junto. Fora da transação, a operação sobrevive e pode ficar sem rastro. Qual você escolhe para **tentativa negada**?
- Hash encadeado detecta adulteração depois do fato. Impedir de verdade exigiria armazenamento externo ou assinatura por terceiro. Onde está o suficiente para este caso?
- Selar períodos permite expurgar o passado e exige guardar as âncoras para sempre. O que você guarda e por quanto tempo?

---

> **Execução sem IA — apenas autocomplete padrão do editor.** Vale para o pré-requisito (a aplicação de documentos e a regra de acesso) e para o desafio: o mecanismo append-only, o encadeamento, o verificador, a política de retenção e os testes são seus. A IA pode construir apenas o **gerador do dataset**, e responder dúvidas conceituais sem entregar a solução.
