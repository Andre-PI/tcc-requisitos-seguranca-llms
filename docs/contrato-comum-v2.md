# Contrato comum v2

Decisão registrada em 3 de novembro de 2026, ainda sem avaliação do orientador.

## Problema

As tarefas exploratórias enviam a todos os níveis um contrato de integração, necessário para executar os testes. Na versão 1, esse texto também trazia indícios das defesas avaliadas. Na T07, por exemplo, ele citava o delimitador `--`, e as oito respostas o utilizaram. Assim, a comparação entre níveis não permitia distinguir o efeito do requisito de segurança do efeito do próprio contrato.

## Regra adotada

O contrato comum contém somente o necessário para a aplicação ser executada e avaliada: módulo e instância, rota, campos, formato da resposta, variáveis de ambiente, interface dos colaboradores e versões do ambiente. Não contém orientações sobre como resolver a tarefa com segurança. Os requisitos de proteção permanecem no complemento de N3.

Consequentemente, N0 não é uma solicitação totalmente livre: é uma frase funcional acrescida dessa convenção. Essa condição deve constar na metodologia. Sem o contrato, parte das respostas de N0 não poderia ser submetida aos mesmos testes.

## Alterações

| Tarefa | Retirado do contrato comum |
|---|---|
| T03 | Restrição a PNG e JPEG, preservação visual e independência dos arquivos, mantidas em N1 ou N3 |
| T04 | Nenhuma alteração |
| T05 | Menção a campos JSON adicionais enviados pelo cliente |
| T07 | Delimitador `--` e aviso de que o utilitário pode falhar |
| T08 | Tipos dos documentos de exemplo, indicando números finitos e chaves textuais |

Os catálogos novos estão em `tarefas/v2/`. Os originais continuam em `tarefas/`, pois os planos e hashes das coletas anteriores dependem deles. Os enunciados de N0 a N3, o sufixo e os verificadores não mudaram.

## Limites

A lista de dependências continua indicando bibliotecas disponíveis, como Pillow na T03 e PyYAML na T08. Ela informa o ambiente, mas também pode influenciar a escolha da solução. A T05 ainda precisa de outra correção antes de nova coleta: declarar a dependência de validação de e-mail e usar endereços de teste aceitos pelo validador. As tarefas T01, T02 e T06, do piloto, ainda não têm contrato nesse formato, e T09 e T10 ainda não existem.

As coletas com o contrato v1 ficam preservadas como registro exploratório e não se misturam às novas.
