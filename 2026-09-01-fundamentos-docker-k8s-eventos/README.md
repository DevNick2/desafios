# Fundamentos: Container + Kubernetes + Event-Driven (Fase 1 de 2)

**Nível:** Iniciante

**Fase 2 (depende desta):** [desafios/2026-09-01-k8s-eventos-arquitetura](../2026-09-01-k8s-eventos-arquitetura/README.md)

## Motivação

Você já tem um desafio Especialista pronto (Fase 2) sobre Kubernetes + arquitetura orientada a eventos, ligado a uma vaga real de Tech Lead (detalhes da empresa omitidos de propósito, para permitir compartilhar este desafio publicamente). Mas você não tem nenhuma experiência prática com Kubernetes ainda — então esse desafio quebra em duas fases: aqui você constrói a base hands-on (containerizar, subir um cluster local, entender os objetos básicos, escalar manualmente); na Fase 2 você aplica isso a um cenário de nível sênior/entrevista.

Você já tem event-driven na mão, só que sem container nem Kubernetes: o repositório `rabbitmq/` tem um publisher (`send.js`, `newTask.js`) e consumers (`worker.js`, `fairDispatchWorker.js`) reais usando `amqplib`. Essa fase reaproveita esse código como ponto de partida — você não vai escrever a lógica de fila do zero, vai aprender a *rodar isso em container e depois em Kubernetes*.

## Conceitos (leia antes de começar)

**Docker: imagem vs. container.** Uma imagem é um pacote read-only (código + dependências + runtime); um container é uma instância em execução dessa imagem. Um `Dockerfile` descreve como construir a imagem, camada por camada — cada instrução (`RUN`, `COPY`) vira uma camada, e o Docker reaproveita camadas não mudadas em builds seguintes (por isso a ordem das instruções importa: o que muda menos vai primeiro).

**Kubernetes: os 4 objetos que você precisa agora.**
- **Pod** — a menor unidade executável; normalmente 1 container por pod (pode ter mais, mas não neste desafio). Pods são efêmeros — não confie na identidade de um pod específico.
- **Deployment** — declara "quero N réplicas deste Pod rodando sempre"; se um pod morre, o Deployment sobe outro. É o que você usa pra rodar sua aplicação.
- **Service** — dá um endereço de rede estável para um grupo de Pods (que têm IPs que mudam toda hora). Sem Service, você não tem como um Pod falar com outro de forma confiável.
- **ConfigMap** — injeta configuração (ex.: host/porta do RabbitMQ) nos Pods sem hardcodar no código ou na imagem.

**Event-Driven: o padrão que você já usa.** Um *producer* (`send.js`) publica uma mensagem numa fila; um ou mais *consumers* (`worker.js`) processam mensagens da fila de forma assíncrona e desacoplada do producer. `fairDispatchWorker.js` já resolve um problema real desse padrão: distribuição justa de trabalho entre múltiplos consumers (`prefetch(1)` — um worker só pega a próxima mensagem depois de confirmar a anterior).

## Objetivo

1. **Containerizar** o publisher e o worker do `rabbitmq/` — um `Dockerfile` simples para cada (não precisa multi-stage ainda, isso é tema de outro desafio).
2. **Rodar tudo localmente com Docker Compose**: RabbitMQ (imagem oficial `rabbitmq:management`) + seu worker containerizado + seu publisher containerizado, na mesma rede. Você já domina Compose — esse passo é o aquecimento antes de Kubernetes.
3. **Subir um cluster Kubernetes local** — escolha `kind` ou `minikube` (sua decisão, documente por quê) — e escrever, **você mesmo**, os manifests YAML (Deployment + Service para RabbitMQ, Deployment + ConfigMap para o worker) para deployar a mesma coisa que rodou no Compose.
4. **Escalar manualmente**: `kubectl scale deployment <worker> --replicas=3`, publicar várias mensagens de uma vez, e observar (via `kubectl logs -f` em cada pod) como o `fairDispatchWorker.js` distribui o trabalho entre os 3 workers.
5. **Fechar com uma reflexão curta**: por que escalar esse worker por CPU (o padrão mais comum de HPA) não faz muito sentido? O que você mediria em vez disso? (Não precisa implementar — é preparação conceitual pra Fase 2.)

## Requisitos

- Documento escrito (Markdown) relatando o que você fez, decisões tomadas e o que observou — não precisa ser um tutorial, mas precisa ter evidência real (comandos rodados, saída observada, não só "funcionou").
- Os manifests YAML do passo 3 são seus, escritos por você — não copiados de um tutorial sem entender cada linha.
- A reflexão do passo 5 tem 3-5 frases, sem jargão solto — se você disser "porque CPU não reflete a carga real", explique o que refletiria.

## Critérios de aceite

- [ ] RabbitMQ, worker e publisher rodam via Docker Compose local, mensagens fluem do publisher ao worker de ponta a ponta.
- [ ] Cluster Kubernetes local rodando com RabbitMQ e worker deployados via manifests YAML próprios.
- [ ] Documento explica, com suas palavras, a diferença entre Pod, Deployment e Service (sem colar definição de doc).
- [ ] Escalonamento manual testado (`kubectl scale`) e o comportamento do `fairDispatchWorker.js` com múltiplos workers está documentado com evidência real.
- [ ] Reflexão sobre HPA por CPU vs. profundidade de fila presente e específica.

## Execução

Sem assistência de IA — apenas autocomplete padrão do editor. Quando terminar, volte e peça revisão (skill `professor-mentor`, modo Revisão). Só depois de concluir esta fase parte para a Fase 2.
