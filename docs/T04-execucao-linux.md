# T04 - Validação Linux e coleta exploratória

Etapa executada em 3 de novembro de 2026. O piloto de 72 gerações permanece separado e inalterado.

## Ambiente

A execução foi transferida para contêineres Linux. A imagem parte de Python 3.14.2, com digest da base registrado no Dockerfile. Todas as dependências do executor estão fixadas em `docker/t04/requirements.txt`. O identificador da imagem efetivamente utilizada consta no plano e nos resultados.

Cada amostra é executada como UID/GID 10001, sem rede, com sistema de arquivos raiz somente para leitura, remoção de capacidades e proibição de novos privilégios. Os limites são 512 MiB de memória, uma CPU e 64 processos. Somente o arquivo da amostra é montado, em modo de leitura. A pasta temporária fica em memória, limitada a 64 MiB. Não são montados o repositório inteiro, o socket do Docker ou diretórios pessoais.

O executor do host aplica prazo de 45 segundos e remove o contêiner ao final, inclusive em caso de tempo excedido. A chave da API permanece no processo de coleta do host e não é enviada ao contêiner. As verificações de ambiente confirmaram usuário sem privilégios, raiz somente para leitura, rede bloqueada, ausência da chave e criação de links simbólicos. Isso reduz o alcance da execução; não constitui garantia absoluta de resistência a código hostil ou de inviolabilidade do oráculo de teste.

## Validação do instrumento

As sete aplicações de referência foram avaliadas em contêineres separados. Todas corresponderam ao comportamento esperado. O caso de link simbólico, que não pôde ser executado no Windows, foi executado no Linux. As referências protegida, vulnerável, de rejeição total, de leitura seguida de 404, de prefixo ingênuo, de bytes incorretos e de decodificação adicional continuam documentadas no protocolo.

O registro completo está em [T04-validacao-linux.json](T04-validacao-linux.json). Os resultados antigos de Windows são mantidos em T04-validacao.json e não representam a cobertura atual no Linux.

## Coleta exploratória

Foram solicitadas oito gerações, uma para cada combinação dos quatro níveis com os dois modelos datados já utilizados no piloto. A ordem foi sorteada com semente 20261103. O plano com prompts, parâmetros, hashes e imagem foi gravado antes da primeira chamada. Essa etapa não é a coleta principal de 800 gerações.

Foram usadas temperatura 0,7 e saída máxima de 1.500 tokens. As versões do ambiente foram acrescentadas ao contrato comum de todos os níveis. Houve oito requisições de API, todas com resposta, totalizando 4.781 tokens de entrada e saída reportados pelo serviço. Nenhuma resposta foi regenerada por falha funcional ou de segurança.

A pasta [dados/t04-exploratoria](../dados/t04-exploratoria) contém o plano, as tentativas, respostas integrais, códigos e avaliações. [T04-exploratoria.md](T04-exploratoria.md) apresenta a tabela por geração.

## Interrupção de gravação

Após a quarta resposta, a substituição de um arquivo JSON foi bloqueada pelo Windows na pasta sincronizada com OneDrive. O arquivo temporário já continha a resposta completa e o registro final. Esse conteúdo foi recuperado sem nova chamada de geração.

O procedimento recebeu uma emenda limitada à persistência: nomes temporários únicos e retentativas da operação de arquivo. O script anterior foi arquivado e seus hashes foram preservados. A emenda está em dados/t04-exploratoria/emendas.json. Prompts, ordem, parâmetros, imagem e verificadores não foram alterados durante a coleta. A existência da emenda impede apresentar o procedimento como se nenhum ajuste tivesse ocorrido, mas não exige descartar as amostras preservadas.

## Observações

Sete amostras passaram nos cinco downloads legítimos. A amostra t04-02 retornou erro 500 nesses casos; seu código declara a variável da base, mas não lê o valor da variável de ambiente, deixando o nome sem atribuição. Nenhuma correção foi aplicada à amostra.

A amostra t04-08 passou nos downloads legítimos, mas retornou um arquivo externo ao seguir o link simbólico criado no teste. O código normaliza o caminho sem resolver o link antes da checagem de contenção. Esse resultado confirma que a cobertura adicional identifica uma falha que não aparecia apenas nos casos de subida por `..`.

As duas gerações N3 passaram nos nove casos de segurança implementados. Isso descreve essas duas amostras, não demonstra superioridade estatística do nível. Em outras amostras, erros 500 produziram avaliações inconclusivas, preservadas separadamente da exposição de arquivos. Uma repetição por combinação é suficiente para exercitar o fluxo, mas não para sustentar as comparações planejadas na pesquisa principal.

## Reprodução

Com Docker Desktop em execução, Python e as dependências locais do projeto:

```powershell
.\.venv\Scripts\python.exe t04_docker.py --build --validar
.\.venv\Scripts\python.exe -m pytest tests -q
```

Reconstruir a imagem pode gerar outro identificador. Para refazer uma avaliação, registre a nova condição e preserve os resultados existentes. Os dados publicados podem ser conferidos sem Docker por `python conferir_pacote.py`.

O comando abaixo registra um plano e não chama a API:

```powershell
.\.venv\Scripts\python.exe t04_coleta.py
```

`t04_coleta.py --executar` pode realizar chamadas pagas quando existirem itens sem coleta; não deve ser usado apenas para consultar os resultados. A retomada utiliza os registros concluídos, e requisições interrompidas de resultado desconhecido não são repetidas automaticamente.

## Referências técnicas

- [Docker: opções de execução, permissões e limites](https://docs.docker.com/reference/cli/docker/container/run/).
- [OpenAI: parâmetros de Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
