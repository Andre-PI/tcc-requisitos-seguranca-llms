# Como utilizar os dados do piloto no artigo

O piloto cumpre duas funções: avaliar a viabilidade dos instrumentos de medição e identificar decisões metodológicas que precisam ser fixadas antes da coleta principal. Ele não deve ser descartado, mas tampouco apresentado como confirmação definitiva das hipóteses.

A análise estática examinou 72 gerações e apontou quatro ocorrências de tokens fixos em duas amostras. O verificador comportamental, por sua vez, identificou exposição de pedidos nas seis amostras T06/N0, demonstrando que aqueles alertas estáticos não cobriam a propriedade de autorização testada. Em T01, cinco das seis amostras N3 bloquearam tentativas por conta e IP dentro do critério operacional adotado; a outra apresentou travamento. São observações descritivas, condicionadas aos adaptadores e aos limites do teste.

A bateria de aceitação ampliada produziu 1.797 resultados de casos nas execuções concluídas. A unidade de análise continua sendo a geração, e não cada chamada HTTP. No grupo de capacidades funcionais básicas, as 72 gerações se distribuíram assim:

| Tarefa | Aprovadas | Reprovadas | Sem execução conclusiva | Total |
|---|---:|---:|---:|---:|
| T01 — login | 22 | 1 | 1 | 24 |
| T02 — busca de produtos | 16 | 5 | 3 | 24 |
| T06 — pedidos | 19 | 3 | 2 | 24 |
| Total | 57 | 9 | 6 | 72 |

O contrato detalhado N1 possui resultados próprios. Ele não deve ser usado para afirmar que N0 descumpriu requisitos que não recebeu. Da mesma forma, não se deve calcular uma taxa global misturando os 62 casos de cada execução T02 com os 11 de T01/T06: isso daria peso maior a uma tarefa apenas por sua bateria ser mais extensa.

A revisão dos sete casos inicialmente problemáticos mostrou causas diferentes. Três passaram ao utilizar Pydantic 1, em comparação controlada, e devem ser discutidos como sensibilidade ao ambiente. Um caso travou devido à aquisição repetida de um lock não reentrante. Outro depende de complementação do contrato ORM; seu funcionamento sob complementação foi documentado como condição adicional. Esses resultados impedem atribuir automaticamente toda falha funcional ao endurecimento de segurança.

## Texto-base para a seção de estudo piloto

O estudo piloto foi utilizado para avaliar a viabilidade do procedimento de geração e dos instrumentos de análise. Foram coletadas 72 implementações, distribuídas entre três tarefas, quatro níveis de especificação, dois modelos e três repetições. A avaliação combinou análise estática, verificações comportamentais de propriedades específicas de segurança e testes de aceitação funcional. Os resultados indicaram a necessidade de distinguir ausência de alertas, aprovação em um teste de segurança, falha funcional e impossibilidade de execução. A revisão das ocorrências também revelou sensibilidade às versões das bibliotecas e à política de complementação de infraestrutura. Por essa razão, os resultados do piloto foram tratados como exploratórios e utilizados para orientar a definição do protocolo da coleta principal.

Este parágrafo descreve o que já foi realizado. Não afirma que a coleta definitiva ocorreu ou que as hipóteses foram confirmadas.

## Decisões para a coleta principal

O ambiente deve ser versionado e informado de modo uniforme quando necessário. A política de adaptadores deve estabelecer quais contratos externos podem ser fornecidos e quais alterações caracterizam reparo da implementação. Convenções ainda não determinadas pelos prompts, como ordenação ascendente, preços iguais aos limites e representação de listas, precisam ser incorporadas ao protocolo antes da coleta. A inclusão desses detalhes não pode eliminar N1 nem introduzir requisitos de segurança nesse nível.

Os resultados inconclusivos devem continuar visíveis no denominador total. Comparações condicionadas somente às aplicações executáveis podem ser apresentadas como análise adicional, com o denominador explícito. A amostra estratificada de revisão manual e as demais sete tarefas permanecem necessárias para a coleta principal. Uma revisão feita pelo assistente não substitui a avaliação humana independente prevista para o artigo.

As tabelas por modelo e nível estão em `resultado-aceitacao.md`. Os arquivos `aceitacao-por-geracao.csv` e `aceitacao-por-caso.csv` permitem reproduzir os agregados. A origem e a interpretação dos sete casos estão em `revisao-sete-casos.md`.
