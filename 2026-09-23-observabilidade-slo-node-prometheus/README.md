# Observabilidade e SLO em uma API de cotação de frete

**Nível:** Avançado (pl↔sr)

---

## Motivação

Vagas de Tech Lead pedem "monitoramento", "observabilidade" e "confiabilidade" com frequência, mas quase sempre como uma linha solta no meio dos requisitos — o que esconde que isso é uma disciplina com decisões de arquitetura próprias, não um checkbox de instalar agente. Nos seus desafios anteriores, observabilidade apareceu sempre como sub-requisito ("log estruturado e contadores"), nunca como o problema central.

Este desafio inverte isso: a API já funciona, e **todo o trabalho é torná-la operável**. O que se aprende aqui não é "usar Prometheus" — é decidir o que medir, o que **não** medir, e como provar que o sistema está saudável sem afogar quem está de plantão.

(Detalhes da empresa de origem omitidos de propósito.)

---

## Pré-requisito

Antes do desafio, construa a API que será instrumentada. **Este código é seu** — a IA não escreve a regra de negócio abaixo.

### `POST /shipping/quote`

Recebe:

```json
{
  "origin_zip": "13087",
  "destination_zip": "90230",
  "weight_kg": 4.3,
  "declared_value_brl": 890.00,
  "service_level": "express"
}
```

`service_level` aceita `standard`, `express` ou `same_day`.

### Regra de cálculo

**1. Zona.** Use os 2 primeiros dígitos de cada CEP (`prefix`):

| Condição | `zone` | Tarifa base |
|---|---|---|
| prefixos iguais | `local` | R$ 12,00 |
| prefixos diferentes, mas `prefix / 10` (divisão inteira) igual | `regional` | R$ 21,50 |
| demais casos | `national` | R$ 38,00 |

Exemplo: `13` e `13` → `local`. `13` e `19` → ambos dão 1, então `regional`. `13` e `90` → `national`.

**2. Peso.** A tarifa base cobre até 2 kg. Cada quilo adicional, **arredondado para cima**, custa:

| `zone` | Preço por kg adicional |
|---|---|
| `local` | R$ 4,20 |
| `regional` | R$ 6,80 |
| `national` | R$ 9,50 |

Exemplo: 4,3 kg → 2 kg cobertos + 3 kg adicionais (2,3 arredondado para cima).

**3. Seguro.** 1,8% de `declared_value_brl`, com mínimo de R$ 2,50.

**4. Multiplicador de serviço.** Aplicado sobre (base + peso adicional), **antes** de somar o seguro:

| `service_level` | Multiplicador |
|---|---|
| `standard` | 1,0 |
| `express` | 1,65 |
| `same_day` | 2,4 |

**5. Total.** `total_brl = ((base + additional_weight) × service_multiplier) + insurance`, arredondado para 2 casas.

### Regras de rejeição

| Condição | HTTP | `error_code` |
|---|---|---|
| `service_level` é `same_day` e `zone` não é `local` | 422 | `SAME_DAY_UNAVAILABLE` |
| `weight_kg` > 30 | 422 | `MANUAL_QUOTE` |
| payload inválido (campo faltando, tipo errado, CEP fora do formato de 5 dígitos) | 400 | `INVALID_PAYLOAD` |

### Dependência externa

Antes de responder, a API consulta um serviço de transportadora em `POST /carrier/availability`, enviando `zone` e `service_level`, e recebendo `{ "available": true, "carrier_code": "..." }`. Se a transportadora responder `available: false`, a cotação retorna **503** com `error_code` `CARRIER_UNAVAILABLE`.

Esse serviço de transportadora é **peça de apoio** — peça para a IA construir. Ele precisa expor latência artificial e taxa de erro configuráveis (por variável de ambiente ou endpoint de controle), porque o desafio depende de conseguir degradá-lo sob demanda. O gerador de carga também é apoio.

A resposta de sucesso inclui `total_brl`, `zone`, `service_level` e `carrier_code`.

---

## Ambiente de execução

Tudo roda local, sem conta paga.

| Dependência | Como roda |
|---|---|
| Prometheus | Container oficial via `docker compose` |
| Grafana | Container oficial, com provisionamento por arquivo |
| Alertmanager | Container oficial |
| API de cotação | Node.js local (seu código) |
| Serviço de transportadora | Fake de apoio, com latência e taxa de erro controláveis |
| Gerador de carga | `k6` em container, ou script Node — apoio |

---

## Contexto

A API está em produção há seis meses. O time descobre incidentes pelo Slack do cliente, não pelo monitoramento. Já houve dois episódios que ninguém soube explicar depois: em um deles a latência subiu por 40 minutos e voltou sozinha; no outro, cotações `same_day` passaram a falhar durante uma tarde inteira sem que o volume total de erros chamasse atenção, porque `same_day` é uma fração pequena do tráfego.

Você assumiu a responsabilidade técnica pela operação desse serviço.

---

## Objetivo

Tornar a API operável: instrumentada, com SLO declarado, alerta que dispara por sintoma e um painel que responde "o que está quebrado e para quem" sem que ninguém precise abrir o código.

---

## Requisitos

**1. Métricas RED do endpoint.** Taxa, erros e duração de `POST /shipping/quote`. A duração é um histograma — escolha os buckets de propósito e **justifique a escolha por escrito**, em função do SLO de latência do requisito 5. Buckets default de biblioteca não passam: ou você os adota conscientemente e explica por quê, ou define os seus.

**2. Orçamento de cardinalidade.** Nenhum label pode conter CEP, valor declarado, `carrier_code` livre ou identificador de requisição. Escreva no repositório o **cálculo da cardinalidade máxima** das suas séries (produto dos valores possíveis de cada label, por métrica) e mantenha o total de séries ativas da sua aplicação **abaixo de 500**. Se um label que você quer não cabe nesse orçamento, a informação vai para log, não para métrica — e isso precisa estar escrito.

**3. Métricas de negócio.** Cotações por `zone` e `service_level`, e rejeições por `error_code`. O segundo incidente do Contexto precisa ser visível aqui: uma falha concentrada em uma fatia pequena do tráfego tem que aparecer, mesmo sem mover o número agregado.

**4. Métricas da dependência.** Latência, falhas e timeouts das chamadas à transportadora, separadas das métricas do seu próprio endpoint. Precisa ficar evidente, no painel, se a lentidão é sua ou dela.

**5. SLO e orçamento de erro.** Declare por escrito, em `SLO.md`:
   - **Disponibilidade:** 99,5% das requisições a `POST /shipping/quote` em 28 dias não retornam 5xx.
   - **Latência:** 95% das requisições bem-sucedidas abaixo de 300 ms em 28 dias.
   - **Decisão que você precisa tomar e justificar:** `SAME_DAY_UNAVAILABLE` e `MANUAL_QUOTE` são 422 — respostas corretas da API a pedidos impossíveis. Eles contam contra a disponibilidade? E `CARRIER_UNAVAILABLE` (503), que é falha de terceiro e não sua? Não existe resposta única; existe resposta defendida.
   - Calcule o orçamento de erro em minutos de indisponibilidade para os 28 dias.

**6. Alerta por taxa de queima.** Implemente alerta de *burn rate* multi-janela no Prometheus: uma janela longa e uma curta em cada severidade (por exemplo, 14,4× em 1h confirmado por 5min para página, 6× em 6h confirmado por 30min para ticket). Alerta preso a sintoma percebido pelo cliente — não crie alerta de CPU, memória ou "serviço caiu".

**7. Log estruturado sem duplicar métrica.** Log em JSON com um identificador de correlação por requisição, propagado para a chamada da transportadora. **Regra:** se uma pergunta é respondida por métrica, o log não a responde de novo. O log existe para o que a métrica não pode carregar por cardinalidade — CEPs, valores, o caso individual. Escreva a divisão que você adotou.

**8. Painel como código.** Dashboard do Grafana versionado em JSON no repositório e carregado por provisionamento — não configurado na mão pela interface. Cada painel responde a uma pergunta declarada em texto; painel sem pergunta é painel a menos.

**9. Prova sob falha.** Dois roteiros executáveis, documentados com os comandos:
   - **Roteiro A:** elevar a latência da transportadora e mostrar o painel identificando a origem e o alerta de latência disparando.
   - **Roteiro B:** fazer `same_day` falhar sem mover de forma perceptível a taxa de erro agregada, e mostrar onde isso aparece.

---

## Critérios de aceite

- [ ] `docker compose up` sobe Prometheus, Grafana, Alertmanager e a transportadora fake; a API sobe local e é raspada com sucesso.
- [ ] `/metrics` expõe as métricas dos requisitos 1, 3 e 4, com os labels dentro do orçamento declarado.
- [ ] O cálculo de cardinalidade está escrito e o total de séries ativas da aplicação está abaixo de 500 — comprovado por uma consulta `count({__name__=~"..."})` registrada no repositório.
- [ ] A escolha dos buckets do histograma está justificada por escrito e é coerente com o SLO de latência.
- [ ] `SLO.md` traz os dois SLOs, a decisão sobre 422 e 503 **com a justificativa**, e o orçamento de erro em minutos.
- [ ] As regras de burn rate estão no Prometheus, com as duas severidades e as janelas curtas de confirmação.
- [ ] O Roteiro A dispara o alerta e o painel mostra que a origem é a dependência, não a API.
- [ ] O Roteiro B é visível no painel de negócio sem exigir leitura de log.
- [ ] O dashboard está versionado em JSON e sobe por provisionamento; cada painel tem sua pergunta escrita.
- [ ] A divisão entre log e métrica está escrita e é respeitada pelo código.

---

## Trade-offs para decidir (não há resposta certa, há resposta defendida)

- Buckets estreitos dão precisão no percentil e custam séries. Onde você corta?
- 422 são erros do cliente. Contá-los como indisponibilidade esconde bugs seus ou infla o alerta?
- Falha da transportadora é indisponibilidade **sua** do ponto de vista de quem chama sua API. Seu SLO mede sua culpa ou a experiência do cliente?
- `carrier_code` é útil para diagnóstico e perigoso como label. Onde ele fica?

---

> **Execução sem IA — apenas autocomplete padrão do editor.** Isso vale para o pré-requisito (a API de cotação e sua regra de negócio) e para todo o desafio: instrumentação, regras de alerta, SLO e dashboard são seus. A IA pode construir apenas as peças de **apoio** — o serviço fake de transportadora e o gerador de carga —, e pode responder dúvidas conceituais sem entregar a solução.
