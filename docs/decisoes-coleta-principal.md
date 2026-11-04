# Decisões para a coleta principal

Registro das decisões tomadas pelo autor antes da coleta principal. Elas serão apresentadas ao orientador com o texto completo.

## Limite de tokens de saída

Decisão de 3 de novembro de 2026: `max_completion_tokens` passa de 1.500 para 4.000 na coleta principal.

Nas 80 gerações exploratórias com o contrato v2, duas foram interrompidas por `finish_reason=length` e não produziram código utilizável: t08v2-04 e t01v2-07, ambas de N3 e do gpt-4.1-mini. Como N3 tende a exigir mais código, o limite anterior afeta os níveis de modo desigual.

As coletas do piloto e as exploratórias usaram 1.500 tokens e foram preservadas nessa condição. Essa diferença deve constar na metodologia, e seus resultados não devem ser combinados com os da coleta principal. Respostas interrompidas continuam sendo registradas, sem regeneração.

## Catálogo de referência

A coleta principal usa os catálogos de `tarefas/v2/`. Na tarefa de recuperação de senha, o catálogo de referência é `T05c.json`. A T04 usa `tarefas/T04.json`, cujo contrato não precisou de corte.

## N0 da T06

Para testar autorização em N0, o contrato da T06 informa a coluna `usuario_id` e a dependência `usuario_atual`. Sem isso, uma aplicação de N0 não teria como verificar o dono do pedido, e a reprovação decorreria da falta de informação. Com isso, N0 recebe parte do conteúdo que no piloto só aparecia em N1, o que pode reduzir a diferença entre esses níveis. Decisão: manter essas informações no contrato e declarar a limitação.

## Modelos

Decisão: usar `gpt-5.4-mini-2026-03-17` e `gemini-3.8-flash`, com `thinkingBudget=0` no Gemini. O segundo substitui o `gpt-4.1-mini-2025-04-14` para que os resultados não dependam de um único provedor. Motivo da configuração e resultados: [coleta exploratória do Gemini](gemini-exploratoria.md).

## Análise estatística

Decisão: desfecho principal por geração, teste de Cochran-Mantel-Haenszel estratificado por tarefa e modelo, ajuste de Holm por questão, análises de sensibilidade para os inconclusivos e revisão manual de 80 gerações sorteadas. Os detalhes estão na subseção 3.5 da [metodologia](metodologia-v05.md). O plano será publicado no repositório antes da primeira chamada.

## Casos fora do desfecho principal

Os casos `excesso_bytes` e `excesso_dimensoes` da T03 e `validade:900` e `validade:901` da T05 verificam valores declarados somente em N3 e são relatados à parte. O executor deve aplicar essa regra. Como consequência, nenhum caso do desfecho principal da T05 verifica expiração; avaliar um caso adicional de token que nunca expira antes da coleta.

## Pendências do executor

- Contar `exposicao` e `acesso_externo_observado` da T04 como falha, relatando-os separadamente.
- Usar os instrumentos v4 em T03 e T04, os v3 em T07, T08, T09 e T10, e a classificação por nível de `resultado_funcional`.
- Interromper a coleta, sem registrar geração, em caso de 429 ou de mudança na versão informada pelo modelo.
- Fixar as regras do Semgrep e incluir Bandit e Semgrep.
- Usar `max_completion_tokens=4000`.
