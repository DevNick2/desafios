# Desafio — TDD Estrito com Testes de Caracterização em Código Legado

> Nível: **Avançado** (pl↔sr)
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito, não só o desafio em si.

---

## Motivação

Gap detectado de forma independente em dois processos seletivos recentes (detalhes das empresas omitidos de propósito): testes automatizados/TDD aparecem como competência avaliada, mas você não tem hoje nenhum caso documentado de TDD aplicado na prática — tem esteira de CI/CD madura, mas o "como você desenvolve com testes primeiro" ainda é teórico. Este desafio força o ciclo red-green-refactor de verdade, e resolve o problema mais comum de quem tenta adotar TDD num código já existente: **como introduzir testes com segurança em algo que hoje não tem nenhum**, sem parar tudo para escrever suíte completa antes de qualquer mudança.

## Pré-requisito

Construa, dentro desta pasta, uma pequena API (a linguagem/framework é sua escolha) com um endpoint `POST /frete/calcular` que implementa exatamente esta regra de cálculo de frete:

> - Peso ≤ 1kg: R$12 fixo — R$18 se a região for Norte.
> - Peso entre 1kg e 5kg: R$12 + R$3 por kg excedente; **frete grátis** se o valor do pedido > R$300, exceto para as regiões Norte e Nordeste (nessas, o desconto não se aplica).
> - Peso > 5kg: retorna erro 422 com corpo `{"erro": "FRETE_MANUAL"}` (fora do escopo automatizado).
> - CEP inválido ou fora do Brasil: erro 400.

Entrada: `peso_kg`, `cep`, `valor_pedido`. A região (Norte, Nordeste, Centro-Oeste, Sudeste, Sul) é derivada do prefixo do CEP — defina você mesmo o mapeamento de faixas de CEP por região (existe tabela pública de faixas por UF/região; qualquer mapeamento plausível serve).

Construa essa API **sem nenhum teste automatizado** — como um legado real chegaria até você. Não escreva testes nesta fase: eles são o objeto do desafio, não a preparação dele.

**Dataset:** ao subir a API, semeie (fixture/seed, não precisa ser dinâmico) 15 pedidos de exemplo cobrindo: um pedido de cada região, um pedido exatamente em 1kg e outro exatamente em 5kg (limites de faixa), um pedido de 1-5kg com valor > R$300 em região Sudeste (frete grátis) e outro nas mesmas condições em região Norte (sem o desconto), um pedido > 5kg (caminho de erro manual) e um CEP inválido (caminho de erro 400).

## Contexto

Com o pré-requisito pronto (endpoint de frete com regra real, zero cobertura de testes), você vai adicionar a seguinte funcionalidade nova, usando TDD estrito — e, como ela toca o código legado sem teste, proteger esse código antes de mexer nele:

> **Nova faixa: pedidos entre 5kg e 10kg** deixam de cair no erro `FRETE_MANUAL` e passam a ser calculados como R$45 fixo + 2% do valor do pedido como seguro — **exceto** na região Norte, que continua caindo em cotação manual (`FRETE_MANUAL`).

## Objetivo

Entregar a funcionalidade nova através do ciclo TDD (red → green → refactor), e proteger com testes de caracterização qualquer trecho de código legado sem cobertura que a mudança precise tocar — antes de tocar nele.

## Requisitos

1. **Ciclo TDD documentado** — para a funcionalidade nova, cada incremento precisa seguir: escrever o teste (deve falhar, e falhar pela razão certa — não por erro de sintaxe/import), escrever o código mínimo para passar, então refatorar com os testes verdes. Registre isso de forma visível (commits separados por fase, ou um log no PR/README do desafio) — pelo menos 3 ciclos distintos.
2. **Testes de caracterização antes do refactor** — se a mudança toca uma função/módulo legado sem teste, escreva primeiro um teste que documenta o comportamento *atual* dele (mesmo que esse comportamento tenha problemas) — isso é sua rede de segurança antes de alterar o código.
3. **Cobertura além do caminho feliz** — para a funcionalidade nova: pelo menos 2 casos de borda e 1 caso de erro/validação, além do caso feliz.
4. **Teste de integração real do endpoint** — não só teste unitário isolado; use o banco real ou um double controlado (ex. SQLite in-memory, fixture com transação revertida, testcontainers) para validar o comportamento fim a fim.
5. **Nota de design** — ao final, registre brevemente (2-3 frases) algo que mudou na forma da sua função/módulo *por causa* do processo de TDD — um sinal de que o processo influenciou o design, não só validou depois.

## Critérios de aceite

- Existe evidência real (histórico de commits ou log explícito) de pelo menos 3 ciclos red-green-refactor — não vale escrever o teste depois da implementação e só "encaixar" retroativamente.
- A suíte roda e passa localmente com um único comando.
- Se algum código legado sem teste foi tocado, há teste de caracterização cobrindo o comportamento anterior a essa mudança.
- Cobre caminho feliz, casos de borda e erro — não só o cenário ideal.
- A nota de design explica algo concreto que TDD mudou na estrutura do código, não uma afirmação genérica.
