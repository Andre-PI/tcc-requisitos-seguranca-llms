# Plano da coleta principal

Este plano é publicado no repositório antes da primeira chamada, e a data do commit serve de registro. O detalhamento está na [metodologia](metodologia-v05.md), subseções 3.3 a 3.6. O arquivo [plano.json](../dados/coleta-principal/plano.json) fixa prompts, ordem, parâmetros, imagens e hashes das fontes.

## Desenho

Dez tarefas, quatro níveis, dois modelos e dez repetições: 800 gerações, em ordem sorteada com semente registrada.

| Parâmetro | `gpt-5.4-mini-2026-03-17` | `gemini-3.8-flash` |
|---|---|---|
| Temperatura | 0,7 | 0,7 |
| Limite de saída | 4.000 tokens | 4.000 tokens |
| Raciocínio interno | zero token observado nas coletas | desativado (`thinkingBudget=0`) |

## Instrumentos

| Tarefas | Versão | Relatórios |
|---|---|---|
| T01, T02 e T06 | contrato v2 | `docs/T01-validacao-linux.json`, `T02` e `T06` |
| T03, T04 e T05 | v4 | `docs/instrumentos-v4/` |
| T07, T08, T09 e T10 | v3 | `docs/instrumentos-v3/` |

Bandit 1.9.4 e Semgrep 1.178.0 rodam ao final, em todas as respostas com código. As regras do Semgrep ficam em arquivo local, e seu hash consta do plano. O arquivo não é publicado porque a licença das regras não foi avaliada para redistribuição; ele vem de `https://semgrep.dev/c/p/python` e foi obtido em 3 de novembro de 2026.

## Regras de execução

- Nenhuma regeneração por código inválido, falha funcional ou resposta interrompida.
- Até duas tentativas em erro 5xx ou de transporte, todas preservadas.
- Erros 4xx, como falta de saldo ou cota, interrompem a coleta sem registrar geração, para retomada depois de corrigida a causa.
- A coleta para se a versão informada pelo modelo mudar.
- O executor recusa iniciar se o plano não estiver publicado ou diferir do publicado.

## Análise

O código da análise, `analise_principal.py`, foi escrito antes dos dados e faz parte das fontes com hash registrado.

| Item | Regra |
|---|---|
| Desfecho de segurança | Falha, aprovada, aprovação parcial ou inconclusiva, por geração |
| Fora do desfecho | `excesso_bytes` e `excesso_dimensoes` (T03); `validade:900` e `validade:901` (T05) |
| T04 | `exposicao` e `acesso_externo_observado` contam como falha |
| Comparações | N0-N1 (QP1); N1-N2, N1-N3 e N2-N3 (QP2); funcional (QP3) |
| Teste | Cochran-Mantel-Haenszel com correção de continuidade, estratificado por tarefa e modelo |
| Multiplicidade | Holm dentro de cada questão, com nível de significância de 5% |
| Sensibilidade | Parciais como falha; inconclusivas como falha; inconclusivas como aprovação |
| Por célula | Contagens, proporções e Wilson 95%, sem teste |
| Revisão manual | 80 gerações sorteadas, uma por combinação, listadas no plano |

A implementação do teste foi conferida com o exemplo UCBAdmissions, cujos resultados coincidem com os do R, e com `statsmodels` em 300 conjuntos simulados. A razão de chances e o intervalo coincidem. O valor de p difere só quando a diferença acumulada é menor que 0,5, situação em que ele fica próximo de 1. Qualquer análise fora deste plano será identificada como exploratória.
