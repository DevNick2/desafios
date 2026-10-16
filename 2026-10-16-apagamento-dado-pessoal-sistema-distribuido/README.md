# Apagar de verdade: dado pessoal em sistema com réplica, backup e derivados

**Nível:** Avançado (pl↔sr)

---

## Motivação

"Deletar o usuário" parece a operação mais simples do CRUD e é uma das mais difíceis de fazer **direito**. O registro principal some em um `DELETE`, mas o nome da pessoa continua no log de auditoria, no backup de ontem, na réplica de leitura, na tabela agregada do relatório, no índice de busca e no e-mail que já foi enviado.

Quando existe obrigação legal de apagar com prazo, essa diferença entre "sumiu da tela" e "não existe mais em lugar nenhum" deixa de ser detalhe de engenharia e vira risco. Este desafio existe para enfrentar o problema inteiro: **o que apagar, o que não pode ser apagado, e como provar depois que foi feito**.

---

## Pré-requisito

Antes do desafio, construa o sistema que terá dados apagados. **Este código é seu.**

### Domínio: relatos recebidos por um canal interno

Pessoas enviam relatos, que são triados e tratados. Alguns relatos são identificados, outros anônimos.

### Tabelas

**`reports`** — `id`, `protocol` (string pública), `category` (`conduct` · `safety` · `financial` · `other`), `body` (texto livre), `reporter_id` (nulo quando anônimo), `created_at`, `status` (`open` · `in_review` · `closed`), `severity` (1 a 5)

**`reporters`** — `id`, `full_name`, `email`, `phone`, `document` (CPF), `created_at`

**`report_events`** — `id`, `report_id`, `actor`, `action`, `payload` (JSON), `created_at` — **trilha de auditoria, append-only**

**`report_daily_stats`** — `day`, `category`, `severity`, `count` — **tabela agregada**, reconstruída por um job

**`search_index`** — `report_id`, `tokens` (texto normalizado do `body` e do nome do relator, para busca)

### Regra de negócio — anonimato e retenção

1. **Relato anônimo** tem `reporter_id` nulo, e o `body` pode mesmo assim conter identificação escrita pela própria pessoa. O sistema não pode presumir que anônimo é não identificável.
2. **Prazo de retenção:** relato `closed` há mais de **5 anos** é elegível para expurgo automático.
3. **Relato sob investigação** (`status` diferente de `closed`, ou `severity` 5) **não pode ser apagado**, mesmo a pedido — a obrigação de preservar prova prevalece. A tentativa responde **409** com `RETENTION_HOLD`.
4. **O protocolo sobrevive sempre.** Mesmo após o apagamento, `protocol`, `category`, `severity`, `created_at` e as datas dos eventos permanecem — é o que permite estatística e prova de que o caso existiu.

### Dataset

**Peça para a IA gerar** — é dado de teste:

- **30.000 relatos** em 6 anos, sendo 40% anônimos.
- **9.000 relatores** identificados.
- `report_events`: 4 a 12 eventos por relato, alguns com o nome ou e-mail do relator **dentro do `payload`** — isso é proposital e é metade do desafio.
- `report_daily_stats` populada e consistente com os relatos.
- `search_index` com tokens derivados de `body` e do nome.
- Casos de borda obrigatórios:
  - 300 relatos anônimos cujo `body` contém nome completo, e-mail ou CPF escritos pela própria pessoa;
  - 120 relatos `closed` há mais de 5 anos (elegíveis a expurgo);
  - 80 com `severity` 5 e 150 ainda abertos (ambos sob retenção);
  - 40 relatores com **mais de um relato**, sendo pelo menos um sob retenção e outro apagável;
  - 25 relatos cujo `payload` de evento guarda o e-mail do relator em campo aninhado.

---

## Ambiente de execução

| Dependência | Como roda |
|---|---|
| Banco principal | **Postgres** em container |
| Réplica de leitura | Segunda instância Postgres com replicação, ou um segundo banco sincronizado por job — a escolha é sua e faz parte do desafio |
| Backup | `pg_dump` para arquivo local, com pelo menos **3 gerações** |
| Busca | Índice em tabela mesmo, ou container de OpenSearch se preferir |
| Aplicação | Node.js ou Python local |
| Gerador do dataset | **Apoio** — a IA pode construir |

---

## Contexto

Chegou o primeiro pedido de apagamento. O `DELETE` na tabela `reporters` funciona, a tela para de mostrar a pessoa, e tudo parece resolvido — até alguém buscar o nome dela e encontrar três ocorrências: no `payload` de um evento, no `search_index` e num relato anônimo onde ela mesma se identificou no texto.

---

## Objetivo

Implementar o apagamento de dado pessoal de forma **completa, verificável e compatível com a obrigação de preservar prova** — e provar que funcionou.

---

## Requisitos

**1. Mapa do dado pessoal.** Antes de apagar, documente **onde o dado pessoal vive**: cada tabela, campo e derivado, incluindo `payload` aninhado, índice de busca, agregados e backups. Esse mapa é o entregável mais importante, porque apagar o que você não mapeou é impossível.

**2. Decida entre apagar e tornar irrecuperável.** Para o que não pode sumir (a linha do evento, a contagem do agregado), escolha entre **anonimizar**, **pseudonimizar** ou **crypto-shredding** (guardar o dado cifrado com uma chave por titular e destruir a chave). Justifique por campo — a resposta não é a mesma para `full_name` e para `document`.

**3. Dado pessoal dentro de texto livre.** Os 300 relatos anônimos com identificação no `body` são o caso difícil. Defina e implemente o tratamento, e **seja explícito sobre o limite**: detecção automática erra nos dois sentidos, e o que você faz com a incerteza — revisão humana, marcação para revisão, redação agressiva — é a decisão de engenharia que importa.

**4. Retenção vence o pedido.** Relato sob investigação ou `severity` 5 não é apagado. O pedido fica **pendente**, registrado, e é retomado quando a retenção cair. Um relator com dois relatos, um apagável e um retido, precisa ter o primeiro tratado e o segundo pendente — não é tudo ou nada.

**5. Derivados.** Depois do apagamento: `search_index` sem o termo, `report_daily_stats` ainda batendo com a contagem real, e réplica refletindo o estado. Diga quanto tempo a réplica pode ficar divergente e por que esse atraso é aceitável.

**6. Backups.** Você não vai reescrever backup — e deve dizer isso por escrito. Defina a política: janela de retenção dos backups, o que acontece se um deles for restaurado, e qual mecanismo reaplica os apagamentos pendentes após uma restauração. **Um `DELETE` que o restore desfaz não é apagamento.**

**7. Comprovante.** Ao fim, gerar um registro verificável do que foi feito: o que foi apagado, o que foi anonimizado, o que ficou retido e por quê, com data. Sem expor o dado que acabou de ser removido.

**8. Idempotência e reexecução.** Rodar o mesmo pedido duas vezes não pode falhar nem duplicar efeito. Um pedido interrompido no meio precisa ser retomável.

---

## Critérios de aceite

- [ ] Mapa escrito do dado pessoal, cobrindo tabela, campo, derivado, índice e backup.
- [ ] Decisão por campo entre apagar, anonimizar, pseudonimizar ou crypto-shredding, com justificativa.
- [ ] Teste que busca o nome, o e-mail e o CPF de um titular apagado **em todas as fontes** e não encontra nada: tabela principal, `payload` de evento, `search_index`, réplica.
- [ ] Os 300 relatos com identificação no texto livre tratados, com o limite da abordagem escrito.
- [ ] Teste do relator com dois relatos: um apagado, um pendente por retenção, com o pendente registrado.
- [ ] `report_daily_stats` continua batendo com a contagem real após o apagamento.
- [ ] Política de backup escrita, com o mecanismo de reaplicação após restore.
- [ ] Comprovante gerado, sem vazar o dado removido.
- [ ] Teste de reexecução: rodar duas vezes produz o mesmo estado; interromper no meio e retomar conclui.

---

## Trade-offs para decidir

- Crypto-shredding é elegante e transfere o problema para a gestão de chaves. Quem garante que a chave morreu mesmo?
- Anonimizar o `payload` do evento preserva a trilha e destrói a capacidade de auditar quem fez o quê. Até onde a auditoria precisa do nome?
- Detecção de dado pessoal em texto livre erra. Falso negativo deixa dado; falso positivo destrói prova. Qual erro é mais barato neste domínio?
- Reaplicar apagamentos após restore exige manter uma lista do que foi apagado — ou seja, **guardar um registro sobre quem pediu para ser esquecido**. Como você resolve essa contradição?

---

> **Execução sem IA — apenas autocomplete padrão do editor.** Vale para o pré-requisito e para todo o desafio: o mapa, a estratégia por campo, o tratamento do texto livre, a política de backup e os testes são seus. A IA pode construir apenas o **gerador do dataset**, e responder dúvidas conceituais sem entregar a solução.
