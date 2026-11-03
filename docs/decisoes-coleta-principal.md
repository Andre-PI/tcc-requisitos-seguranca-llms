# Decisões para a coleta principal

Registro das decisões tomadas antes da coleta principal. Ainda não foram avaliadas pelo orientador.

## Limite de tokens de saída

Decisão de 3 de novembro de 2026: `max_completion_tokens` passa de 1.500 para 4.000 na coleta principal.

Nas 80 gerações exploratórias com o contrato v2, duas foram interrompidas por `finish_reason=length` e não produziram código utilizável: t08v2-04 e t01v2-07, ambas de N3 e do gpt-4.1-mini. Como N3 tende a exigir mais código, o limite anterior afeta os níveis de modo desigual.

As coletas do piloto e as exploratórias usaram 1.500 tokens e foram preservadas nessa condição. Essa diferença deve constar na metodologia, e seus resultados não devem ser combinados com os da coleta principal. Respostas interrompidas continuam sendo registradas, sem regeneração.

## Catálogo de referência

A coleta principal usa os catálogos de `tarefas/v2/`. Na tarefa de recuperação de senha, o catálogo de referência é `T05c.json`. A T04 usa `tarefas/T04.json`, cujo contrato não precisou de corte.

## Questão em aberto: N0 da T06

Para testar autorização em N0, o contrato da T06 informa a coluna `usuario_id` e a dependência `usuario_atual`. Sem isso, uma aplicação de N0 não teria como verificar o dono do pedido, e a reprovação decorreria da falta de informação. Com isso, N0 recebe parte do conteúdo que no piloto só aparecia em N1, o que pode reduzir a diferença entre esses níveis. A versão atual mantém essas informações no contrato. A escolha deve ser avaliada com o orientador antes da coleta principal.
