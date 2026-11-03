# Requisitos, segurança e correção funcional de código gerado por LLMs

Este repositório reúne os códigos, dados e procedimentos do meu TCC em Engenharia de Software no iCEV, sob orientação do professor Mauro José Araújo de Melo.

A pesquisa investiga como o detalhamento dos requisitos influencia a segurança do código gerado por modelos de linguagem e se há perda de funcionalidade associada. As tarefas utilizam Python e FastAPI.

## Estudo piloto

O piloto foi realizado com 72 gerações: três tarefas, quatro níveis de especificação, dois modelos e três repetições por condição. As tarefas são login, busca de produtos e consulta de pedidos. Os modelos utilizados foram `gpt-4.1-mini-2025-04-14` e `gpt-5.4-mini-2026-03-17`.

| Nível | Especificação |
|---|---|
| N0 | Descrição funcional mínima |
| N1 | Descrição funcional detalhada |
| N2 | N1 com orientação genérica de segurança |
| N3 | N1 com requisitos específicos de segurança |

A avaliação combina Bandit e Semgrep, testes de aceitação e verificações de autorização e bloqueio de tentativas de login. No conjunto funcional mínimo, 57 gerações foram aprovadas, nove reprovadas e seis ficaram sem execução conclusiva.

Os resultados são preliminares. Os testes ampliados foram definidos após a coleta, e algumas falhas dependem das versões das bibliotecas. O experimento principal, previsto para 800 gerações, ainda não foi executado.

## Documentos e resultados

- **Referencial teórico:** [PDF](orientacao/Referencial-teorico-v04.pdf) e [Word](orientacao/Referencial-teorico-v04.docx).
- **Metodologia:** [PDF](orientacao/Metodologia-v04.pdf) e [Word](orientacao/Metodologia-v04.docx).
- **Resultados do piloto:** [PDF](orientacao/Resultados-piloto-v01.pdf) e [Word](orientacao/Resultados-piloto-v01.docx), versão parcial para orientação.
- [Exemplo de análise de acesso a pedidos](exemplos/acesso-a-pedidos.md), com prompt, código e resultado do teste.
- [Resultados funcionais](docs/resultado-aceitacao.md).
- [Resultados comportamentais](docs/resultado-comportamental.md).
- [Protocolo dos testes e limitações](docs/protocolo-comportamental.md).

## Ampliação das tarefas

A T04, download de arquivos, foi validada em Linux com links simbólicos e sete aplicações de referência. Uma coleta exploratória separada reuniu oito gerações, executadas em contêineres sem rede. Consulte o [procedimento](docs/T04-execucao-linux.md) e os [resultados](docs/T04-exploratoria.md). O piloto e a coleta principal permanecem separados dessa etapa.

A T03, upload de fotos, tem [protocolo e verificador](docs/T03-protocolo.md) validados contra nove aplicações de referência em Linux. A [coleta exploratória](docs/T03-exploratoria.md) reuniu oito respostas; seis passaram nos uploads legítimos, uma retornou erro 500 e outra não importou no ambiente fixado. A [leitura dos resultados](docs/T03-leitura-resultados.md) detalha os critérios e as falhas observadas.

A T05, recuperação de senha, tem [contrato e testes](docs/T05-protocolo.md) validados com 11 aplicações de referência. A [coleta exploratória](docs/T05-exploratoria.md) reuniu oito respostas: uma executou no ambiente fixado e sete tiveram impedimentos de importação. O [relatório e a revisão dos tokens](docs/T05-leitura-resultados.md) apresentam o diagnóstico posterior, com dependência opcional e endereços compatíveis, em que sete códigos passaram no ciclo funcional. Os resultados originais foram preservados; a revisão assistida por IA aguarda conferência humana independente.

A T07, relatório com utilitário externo, tem [protocolo e verificador](docs/T07-protocolo.md) validados contra dez aplicações de referência no Linux. A [coleta exploratória](docs/T07-exploratoria.md) reuniu oito respostas; sete passaram nos relatórios legítimos e uma não importou. O [relatório e a revisão da invocação](docs/T07-leitura-resultados.md) registram ausência de marcadores nos vetores das sete amostras executáveis e cinco reprovações no tratamento de falhas do utilitário. A revisão assistida por IA aguarda conferência humana independente.

Essa primeira coleta da T07 foi afetada pelo texto comum a todos os níveis, que citava o delimitador `--`. Com o [contrato comum revisado](docs/contrato-comum-v2.md), uma [nova coleta exploratória](docs/T07-exploratoria-v2.md) de oito respostas teve seis amostras executáveis. Quatro delas, em N0, N1 e N2, deixaram uma opção injetada chegar ao utilitário; as duas de N3 usaram o delimitador e passaram. Os registros da primeira coleta foram preservados. Os catálogos revisados das demais tarefas estão em `tarefas/v2/`, ainda sem nova coleta.

A T08, importação de configuração YAML, tem [protocolo e verificador](docs/T08-protocolo.md) validados contra 11 aplicações de referência no Linux, com 24 cenários por aplicação. Os casos de desserialização insegura só criam arquivos marcadores fictícios e são executados em contêiner sem rede. Ainda não há gerações de LLM para essa tarefa.

## Arquivos

| Caminho | Conteúdo |
|---|---|
| `codigos/` | As 72 implementações geradas, preservadas sem reparos |
| `dados/` | Exportações dos prompts, respostas, achados e resultados |
| `resultados.db` | Banco SQLite com os registros e o histórico das verificações |
| `relatorios-sast/` | Relatórios do Bandit e do Semgrep |
| `execucoes/` | Códigos, respostas e erros das execuções selecionadas |
| `docs/` | Critérios, protocolos e relatórios |
| `tests/` | Testes dos verificadores |

## Conferência dos dados

Com Python 3.11 ou posterior:

```powershell
python conferir_pacote.py
```

O comando confere os hashes dos arquivos, as contagens e a correspondência entre os códigos e o banco. Não chama a API nem executa os programas gerados. Os hashes permitem detectar alterações nos arquivos; não comprovam a autenticidade da coleta.

## Execução dos testes

O ambiente do piloto utiliza Python 3.14.2. As dependências estão em `requirements-lock.txt`. Execute em uma cópia do repositório, pois os verificadores acrescentam registros ao banco.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

Para repetir os testes das duas amostras apresentadas no exemplo:

```powershell
.\.venv\Scripts\python.exe validar_aceitacao.py --ids 25 34
.\.venv\Scripts\python.exe verificar.py --ids 25 34
```

Esses comandos executam as aplicações geradas sob as condições descritas no protocolo. Os diretórios históricos dos registros se referem à máquina de coleta. A análise estática utilizou as regras `p/python` do Semgrep, cujo conteúdo remoto pode mudar.

Consultar os dados e executar os testes não exige chave de API. O script `piloto.py` é usado para novas gerações e realiza chamadas pagas quando executado nessa modalidade.
