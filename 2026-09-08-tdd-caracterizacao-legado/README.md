# Desafio — TDD Estrito com Testes de Caracterização em Código Legado

> Nível: **Avançado** (pl↔sr)
> Desafio autônomo — o pré-requisito abaixo é construído por você dentro desta pasta, sem depender de nenhum outro repositório seu.
> Execução sem IA — apenas autocomplete padrão do editor. Isso inclui a construção do pré-requisito, não só o desafio em si.

---

## Motivação

Gap detectado de forma independente em dois processos seletivos recentes (detalhes das empresas omitidos de propósito): testes automatizados/TDD aparecem como competência avaliada, mas você não tem hoje nenhum caso documentado de TDD aplicado na prática — tem esteira de CI/CD madura, mas o "como você desenvolve com testes primeiro" ainda é teórico. Este desafio força o ciclo red-green-refactor de verdade, e resolve o problema mais comum de quem tenta adotar TDD num código já existente: **como introduzir testes com segurança em algo que hoje não tem nenhum**, sem parar tudo para escrever suíte completa antes de qualquer mudança.

## Pré-requisito

Construa, dentro desta pasta, uma pequena API (a linguagem/framework é sua escolha) com pelo menos um endpoint que aplica uma regra de negócio genuína e com alguma complexidade real — ex: cálculo de frete com múltiplas faixas, motor de elegibilidade de desconto com várias condições encadeadas, validação de pedido com regras de transição de estado.

Construa essa API **sem nenhum teste automatizado** — como um legado real chegaria até você. Não escreva testes nesta fase: eles são o objeto do desafio, não a preparação dele.

## Contexto

Com o pré-requisito pronto (endpoint(s) com regra de negócio real, zero cobertura de testes), você vai adicionar uma funcionalidade nova pequena a esse endpoint, usando TDD estrito — e, como a mudança vai tocar código legado sem teste, proteger esse código antes de mexer nele.

Exemplos de funcionalidade nova pequena o suficiente para o escopo: um filtro adicional numa listagem, uma regra de validação de negócio nova, um cálculo derivado a partir de campos já existentes, uma nova condição de autorização.

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
