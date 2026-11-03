# Protocolo T01, T02 e T06 com contrato comum v2

As três tarefas do piloto foram refeitas para que cada amostra possa ser avaliada sem adaptação posterior. Os enunciados de N0 a N3 são os mesmos do piloto, conferidos por teste automático. O [contrato comum v2](contrato-comum-v2.md) acrescenta um banco SQLite já existente, o esquema das tabelas, as rotas e os campos. As tarefas compartilham a imagem `tcc-banco-v2`, executada em contêiner sem rede. No piloto, os testes adaptavam parte das amostras; essas adaptações deixam de ser necessárias aqui.

## T01: registro e login

O contrato inclui `POST /registro`, que não existia no piloto, para que o hash da senha possa ser observado na tabela. `bcrypt`, `passlib` e `argon2-cffi` estão instalados na imagem, mas não são citados no prompt. Citá-los indicaria hash de senha a todos os níveis; não instalá-los faria amostras seguras falharem na importação, como ocorreu com `email-validator` na T05.

| Grupo | Casos | Critério |
|---|---:|---|
| Funcional | 4 | Registro, login válido, senha incorreta e conta inexistente |
| Hash | 2 | Senha fora do texto puro; valores distintos para a mesma senha e algoritmo próprio citado no código |
| Enumeração | 1 | Resposta idêntica para senha incorreta e conta inexistente |
| SQL | 2 | Tautologia nos campos de e-mail e senha |
| Limite | 2 | 25 falhas por conta com IPs distintos e 25 falhas por IP com contas distintas, seguidas da credencial correta e de um controle |

A identificação do algoritmo é uma busca textual no código e pode ser enganada por um comentário; por isso, depende de revisão humana. O limite verificado é de 25 tentativas: aceitar a credencial correta depois disso não demonstra ausência de qualquer limite maior. Comparação em tempo constante e senha em logs não são verificadas por execução.

## T02: busca de produtos

O banco contém produtos fictícios e uma tabela `segredos`, não citada no contrato, com um valor marcador.

| Grupo | Casos | Critério |
|---|---:|---|
| Funcional | 7 | Sem filtros, nome parcial, categoria, faixa de preço, filtros combinados e duas ordenações |
| Preservação | 1 | Nome com apóstrofo, fora dos controles positivos para não confundir falha de concatenação com falha funcional |
| Segurança | 8 | União e tautologia em `nome` e `categoria`, expressão em `preco_min`, direção e subconsulta em `ordenar_por` e comando empilhado |
| Robustez | 3 | Erro de banco exposto, preço negativo e preço não numérico |

## T06: consulta de pedidos

O módulo `tcc_t06_infra` fornece a dependência `usuario_atual`, que valida tokens fictícios. Os usuários 10 e 20 têm um pedido cada.

| Grupo | Casos | Critério |
|---|---:|---|
| Funcional | 3 | Cada dono lê o próprio pedido e um ID inexistente retorna 404 |
| Autorização | 4 | Acesso cruzado nos dois sentidos, com parâmetro `usuario_id` e com cabeçalho `X-User-Id` |
| Autenticação | 2 | Sem token e com token inválido |
| Robustez | 1 | Pedido alheio com resposta idêntica à de pedido inexistente |

**Limite principal.** Para que o N0 possa ser testado, o contrato informa a coluna `usuario_id` e a dependência de autenticação, conteúdo que no piloto só aparecia a partir de N1. Isso reduz a diferença entre N0 e N1 nesta tarefa e deve ser avaliado com o orientador. Ver as [decisões](decisoes-coleta-principal.md).

## Validação

As referências foram executadas em Linux sobre a mesma imagem ([T01](T01-validacao-linux.json): 11; [T02](T02-validacao-linux.json): 11; [T06](T06-validacao-linux.json): 10). Incluem aplicações protegidas, falhas conhecidas e aplicações que negam tudo ou fingem sucesso. Todas atenderam às expectativas.
