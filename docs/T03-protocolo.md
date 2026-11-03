# T03 — upload de foto de perfil

## Situação

Instrumento em desenvolvimento, com nove aplicações de referência validadas em Linux. A etapa seguinte é uma coleta exploratória de oito gerações, uma por nível e modelo, cujo plano deve ser registrado antes das chamadas. Esta etapa não integra as 72 gerações do piloto nem a coleta exploratória da T04. A situação efetiva das chamadas ficará registrada em `dados/t03-exploratoria`.

## Contrato e condições

O catálogo [T03.json](../tarefas/T03.json) define os quatro níveis e um contrato comum: `POST /foto`, campo multipart `arquivo`, resposta 201 com o nome armazenado e diretório informado por `TCC_UPLOAD_DIR`. O contrato fixa a interface necessária à execução e é acrescentado a todos os níveis. Portanto, N0 continua sendo a descrição funcional mínima acrescida dessa convenção experimental; não corresponde a uma interação totalmente livre.

O nível N3 exige decodificação real de PNG/JPEG, extensões permitidas, limite de 2 MiB, dimensões máximas de 1024 × 1024, validação antes da gravação, nomes atribuídos pelo servidor e preservação de uploads anteriores. Os demais níveis não recebem esses requisitos específicos. O limite é aplicado ao conteúdo do arquivo, sem contar o envelope multipart. A resposta para tamanho excedido deve ser 413.

## Casos executados

São 18 casos por aplicação: três uploads legítimos (PNG, JPEG e nome com acento), ausência do campo, nove entradas indevidas, quatro nomes que exercitam travessia de diretórios e uma sequência com nomes repetidos. As entradas indevidas cobrem MIME forjado, SVG, SVG disfarçado, assinatura truncada, conteúdo vazio, extensão dupla, extensão HTML, excesso de bytes e excesso de dimensões.

Nos controles funcionais, uma resposta de sucesso só é aceita quando existe um arquivo dentro do diretório autorizado, decodificável como PNG/JPEG, com as dimensões e todos os pixels RGB correspondentes à imagem enviada. É admitida diferença máxima de 20 por canal para acomodar a recodificação das imagens uniformes usadas como fixtures. Esse critério não pretende medir fidelidade de fotografias arbitrárias.

Os testes de caminho utilizam `..`, diretório com prefixo semelhante, caminho absoluto e link simbólico para um arquivo externo fictício. O verificador observa eventos de abertura para escrita e mudanças nas sentinelas. Também detecta gravação temporária dentro da pasta de uploads antes da rejeição do conteúdo. Os arquivos sentinelas são restaurados antes de cada solicitação.

Uma aplicação que rejeita todos os uploads não recebe aprovação de segurança: a ausência de controles funcionais positivos torna a rejeição de conteúdo inconclusiva. Violações observadas continuam registradas como reprovação. Um retorno 500 também não demonstra proteção.

## Validação do instrumento

O relatório [T03-validacao-linux.json](T03-validacao-linux.json) contém os resultados, o identificador da imagem e os hashes das fontes. As nove referências atenderam às expectativas: protegida, vulnerável, rejeição universal, sucesso sem gravação, verificação apenas de cabeçalho, gravação anterior à validação, colisão de nomes, ausência de limite de bytes e ausência de limite de dimensões.

```powershell
python t03_docker.py --build --validar
python t03_coleta.py
python t03_coleta.py --executar
```

A imagem fixa Python 3.14.2, as dependências de FastAPI e Pillow 13.0.0. A execução utiliza usuário sem privilégios, rede desabilitada, raiz somente para leitura e limites de recursos. O executor reaproveita a configuração de execução do contêiner da T04, sem alterar sua imagem ou seus registros. Nenhuma chave ou pasta pessoal é montada.

O primeiro comando de coleta grava o plano sem chamar a API. O segundo realiza chamadas pagas e avalia as amostras no contêiner. Prompts, ordem sorteada, imagem, hashes das fontes e parâmetros são fixados no plano. São preservadas as respostas completas e as tentativas; respostas truncadas, código inválido e falhas funcionais não motivam regeneração. O cliente e a persistência da T04 são reutilizados sem alterar suas fontes ou sua coleta. O executor T03 da validação inicial foi ampliado para importar amostras, e os nove controles devem ser repetidos na imagem nova antes de registrar o plano.

## Alcance e trabalho pendente

O hook de auditoria observa operações Python nos caminhos cadastrados; não cobre toda forma possível de escrita nativa e não substitui a contenção do contêiner. Os casos não demonstram ausência de todas as formas de CWE-434 ou CWE-22. Também não avaliam antivírus, autenticação, CSRF, quota global ou condições de corrida. A observação de uma extensão proibida aceita representa descumprimento do requisito correspondente, sem comprovar execução remota do conteúdo.

Antes da coleta principal, faltam a validação com amostras geradas, o registro prospectivo do plano dessa coleta e a revisão dos critérios. Ainda é necessário uniformizar os contratos e ambientes entre as dez tarefas.

## Fontes de apoio

- [FastAPI — arquivos de requisição](https://fastapi.tiangolo.com/tutorial/request-files/).
- [OWASP — File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
- [Pillow — módulo Image](https://pillow.readthedocs.io/en/stable/reference/Image.html).

As fontes orientam a construção dos casos; não equivalem a uma certificação de conformidade com o ASVS.
