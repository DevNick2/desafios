# Desafio — Manutenção e Evolução de uma Tela AngularJS (1.x)

> Nível: **Intermediário** (jr↔pl)
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito, não só o desafio em si.

---

## Motivação

Gap identificado num processo seletivo real para desenvolvedor fullstack sênior (detalhes da empresa omitidos de propósito): a vaga exige **AngularJS** (a versão 1.x, anterior ao Angular moderno) como requisito obrigatório, num time que mantém um produto SaaS em produção há anos. Seu front-end em produção é Vue.js, e o estudo de Angular que você tem é do Angular moderno, que tem outra arquitetura.

Empresas que ainda pedem AngularJS raramente querem código novo nele: querem alguém que **entre numa base antiga, entenda o *digest cycle*, corrija bug sem quebrar o resto e evolua a tela com segurança**. É isso que este desafio treina.

## Pré-requisito

Construa, dentro desta pasta, uma tela **AngularJS 1.8** de **fila de pedidos de um restaurante**, escrita no estilo "clássico" que bases legadas costumam ter: `controller` com `$scope`, um `service` com `$http`, uma diretiva customizada e um filtro customizado. Todo identificador de código em inglês. Implemente exatamente estas regras:

> **Fluxo de status** (`status`): `RECEIVED → PREPARING → READY → DISPATCHED → DELIVERED`. `CANCELLED` só é permitido a partir de `RECEIVED` ou `PREPARING`. Botões de ação só aparecem para a transição válida seguinte; transição inválida nunca chega à API.
>
> **Atraso** (`is_late`): um pedido está atrasado se ainda não chegou em `READY` e o tempo desde `created_at` passou do limite do canal (`channel`): `DELIVERY` 30 min, `TAKEOUT` 20 min, `DINE_IN` 25 min. Pedidos em `READY` ou depois nunca estão atrasados.
>
> **Total exibido:** soma de `quantity × unit_price_cents` dos itens + `delivery_fee_cents` (só para `DELIVERY`), exibido em reais por um **filtro customizado** `brl` (`R$ 1.234,50`).
>
> **Ordenação padrão:** atrasados primeiro; dentro de cada grupo, o mais antigo primeiro.
>
> **Filtros na tela:** por `channel` e por `status` (múltipla seleção), combináveis.
>
> **Diretiva** `<order-timer>`: mostra há quantos minutos o pedido está aberto e fica vermelha quando `is_late`.
>
> **Atualização:** a tela busca `GET /orders` a cada **10 segundos** (polling) e envia transições com `PATCH /orders/{id}` (`{"status": "..."}`).

**Dataset:** 30 pedidos (`id`, `channel`, `status`, `created_at`, `items[]` com `name`/`quantity`/`unit_price_cents`, `delivery_fee_cents`), com estes casos propositais: 1 `DELIVERY` com exatamente 30 min (não está atrasado, fronteira), 1 com 31 min (atrasado); 1 `READY` com 2 horas (não conta como atrasado); 1 `TAKEOUT` com `delivery_fee_cents` preenchido por engano (não deve somar); 1 pedido com 12 itens (layout); 2 `CANCELLED`; pelo menos 3 de cada canal. Os horários são relativos ao momento em que a API fake sobe, para os atrasos continuarem válidos.

A tela e suas regras são **núcleo** e são suas. A **API de pedidos** é só apoio (um servidor fake que serve o dataset e aceita o `PATCH`), porque o que este desafio exercita é o front legado, não o back.

## Ambiente de execução

| Dependência | Como roda |
|---|---|
| AngularJS 1.8 | Pacote `angular` via npm (ou arquivo local); sem CDN obrigatório |
| API de pedidos | Servidor fake local de apoio (Node + Express ou `json-server`), com um parâmetro para gerar **N pedidos sintéticos** além do dataset (usado no requisito de performance) |
| Testes | Karma + Jasmine com Chrome headless, ou Jest + jsdom, com `angular-mocks` |
| Conta / custo | Nenhum |

## Contexto

A tela está "em produção" e três demandas chegaram juntas no seu primeiro sprint no time.

## Objetivo

Atender as três demandas mexendo o mínimo necessário, cobrir a tela com testes antes de mudar comportamento e deixar uma parte dela no padrão de **componentes** do AngularJS 1.5+, que é o caminho recomendado para uma futura migração.

## Requisitos

1. **Testes antes de mudar.** Antes de qualquer demanda, escreva testes que fixem o comportamento atual: o filtro `brl`, a regra de atraso (incluindo as fronteiras do dataset), as transições de status válidas e inválidas, e o `service` com `$httpBackend` do `angular-mocks`.
2. **Demanda 1 — Novo canal `MARKETPLACE`.** Pedidos vindos de marketplace têm limite de atraso de **35 min**, não pagam `delivery_fee_cents` na tela (a taxa é do parceiro) e mostram um selo "Parceiro". Nenhum canal existente pode mudar de comportamento — os testes do requisito 1 precisam continuar passando.
3. **Demanda 2 — Bug "mudei o status e a tela não atualizou".** Reproduza: a transição chama a API por uma função utilitária que usa `fetch` nativo (e não `$http`), e a lista só muda na próxima rodada do polling. Diagnostique **por que** (explique o *digest cycle* no README da solução) e corrija do jeito certo para AngularJS, sem espalhar `$scope.$apply()` pela tela.
4. **Demanda 3 — Tela lenta com muitos pedidos.** Suba a API fake com **600 pedidos**. Meça (ex.: número de *watchers* e tempo do *digest* antes/depois) e reduza o custo usando o que o AngularJS oferece: `track by` no `ng-repeat`, *one-time bindings* (`::`) onde o dado não muda, e menos *watchers* na diretiva `<order-timer>`. Registre as medições.
5. **Vazamento no polling.** Garanta que o `$interval` do polling é cancelado quando a tela é destruída (`$destroy`) e prove com um teste.
6. **Migração parcial para componente.** Reescreva a linha do pedido como `.component('orderRow', …)` com *bindings* de mão única (`<`) e saída por callback (`&`), sem `$scope` dentro do componente. O resto da tela continua no estilo antigo, convivendo com o componente.

## Critérios de aceite

- Todos os testes do requisito 1 passam antes e depois das três demandas.
- Um pedido `DELIVERY` com 30 min não aparece atrasado; com 31 min aparece; um `MARKETPLACE` com 34 min não aparece.
- Depois da correção do bug, a transição de status reflete na tela imediatamente, sem esperar o polling.
- Com 600 pedidos, o número de *watchers* e o tempo de *digest* medidos caem em relação à medição inicial, e o README da solução mostra os números.
- Navegar para fora da tela e voltar 5 vezes não multiplica as chamadas de polling (comprovado por teste ou pelo log da API fake).
- O componente `orderRow` não usa `$scope` e é testado isoladamente com `$componentController`.
