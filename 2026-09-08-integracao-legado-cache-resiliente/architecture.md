Desenho da Solução:

- Endpoint GET /products e /produtcs/{id} para listar e visualizar o produto consulta o service que calcula o preço final;
- ProductService que calcula o preço final de cada produto, esse service chama o ACL para buscar o dado, aqui também vamos usar o retry com backoff;
- ACLService (Anti-corruption layer) para consumir o legado e devolver os dados no formato que a API espera;
- CacheService cuida das operações CRUD do cache, o D é para invalidar o cache, ttl padrão de 15segundos




GET (/products ou /products/{id}) --> ProductService --> ACLService --> Sistema Legado