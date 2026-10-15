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

- **Metodologia:** [PDF](orientacao/Metodologia-v03.pdf) e [Word](orientacao/Metodologia-v03.docx).
- [Exemplo de análise de acesso a pedidos](exemplos/acesso-a-pedidos.md), com prompt, código e resultado do teste.
- [Resultados funcionais](docs/resultado-aceitacao.md).
- [Resultados comportamentais](docs/resultado-comportamental.md).
- [Protocolo dos testes e limitações](docs/protocolo-comportamental.md).

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
