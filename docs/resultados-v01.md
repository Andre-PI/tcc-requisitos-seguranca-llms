## 4 RESULTADOS

### 4.1 Visão geral da coleta principal

A coleta principal reuniu 800 gerações, distribuídas entre dez tarefas, quatro níveis de especificação, dois modelos e dez repetições por combinação. Foram avaliados gpt-5.4-mini-2026-03-17 e gemini-3.8-flash. Cada nível reuniu 200 gerações. Os resultados desta seção não incluem o piloto nem as coletas exploratórias.

As subseções 4.1 a 4.5 apresentam os resultados de segurança com a classificação corrigida pela Emenda 02. A análise estática é apresentada na subseção 4.6, e a revisão manual da subseção 4.7 foi medida contra a classificação registrada, anterior à correção. A subseção 4.8 apresenta também o resultado do critério registrado. A correção da T03 ocorreu depois da coleta e da primeira análise, sem novas chamadas aos modelos.

A proporção de falhas entre gerações conclusivas foi de 53,4% em N0, 50,3% em N1, 21,6% em N2 e 0,0% em N3. O denominador exclui as inconclusivas e inclui as aprovações parciais. Nos casos testados, N3 não apresentou falha observada, mas reuniu 16 aprovações parciais e 18 avaliações inconclusivas.


Tabela 1 - Classificação de segurança e aprovação funcional por nível

| Nível | Falha | Aprovada | Parcial | Inconclusiva | Falha entre conclusivas | Funcional aprovado |
|---|---:|---:|---:|---:|---:|---:|
| N0 | 103 | 72 | 18 | 7 | 53,4% | 195 |
| N1 | 99 | 77 | 21 | 3 | 50,3% | 198 |
| N2 | 42 | 140 | 12 | 6 | 21,6% | 192 |
| N3 | 0 | 166 | 16 | 18 | 0,0% | 180 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


### 4.2 QP1: detalhamento funcional

Na comparação entre N0 e N1, o teste de Cochran-Mantel-Haenszel, com correção de continuidade e estratificação por tarefa e modelo, apresentou p ajustado de 0,490. Não foi demonstrada diferença na frequência de falhas entre essas condições ao nível de significância adotado. As três análises de sensibilidade também apresentaram p ajustado superior a 0,05.

Nas tabelas de comparação, a razão de chances expressa as chances do desfecho no primeiro nível em relação ao segundo. O desfecho é falha de segurança em QP1 e QP2 e reprovação funcional em QP3. Os intervalos são de 95%, e o ajuste de Holm foi aplicado dentro de cada questão.


Tabela 2 - QP1: Análise principal

| Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---:|---|---:|---:|
| N0 × N1 | 1,28 | 0,68 a 2,39 | 0,490 | 0,490 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


Tabela 3 - QP1: análises de sensibilidade

| Análise de sensibilidade | Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---|---:|---|---:|---:|
| Parciais como falha | N0 × N1 | 1,10 | 0,58 a 2,06 | 0,889 | 0,889 |
| Inconclusivas como falha | N0 × N1 | 1,45 | 0,79 a 2,63 | 0,239 | 0,239 |
| Inconclusivas como aprovação | N0 × N1 | 1,21 | 0,66 a 2,22 | 0,592 | 0,592 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


### 4.3 QP2: requisitos de segurança

As comparações N1 × N2, N1 × N3 e N2 × N3 apresentaram p ajustado inferior a 0,001 na análise principal. A razão de chances de N1 em relação a N2 foi de 58,78, com intervalo de 12,24 a 282,25. Nas comparações com N3, a razão de chances principal e seu intervalo não foram calculáveis, diante da ausência de falhas nesse nível.

Os três contrastes mantiveram p ajustado inferior a 0,001 em todas as análises de sensibilidade. Ao contar aprovações parciais ou inconclusivas como falha, foi possível calcular a razão de chances nas comparações com N3.


Tabela 4 - QP2: Análise principal

| Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---:|---|---:|---:|
| N1 × N2 | 58,78 | 12,24 a 282,25 | < 0,001 | < 0,001 |
| N1 × N3 | não calculável | não calculável | < 0,001 | < 0,001 |
| N2 × N3 | não calculável | não calculável | < 0,001 | < 0,001 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


Tabela 5 - QP2: análises de sensibilidade

| Análise de sensibilidade | Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---|---:|---|---:|---:|
| Parciais como falha | N1 × N2 | 26,82 | 9,85 a 73,02 | < 0,001 | < 0,001 |
| Parciais como falha | N1 × N3 | 76,57 | 21,14 a 277,30 | < 0,001 | < 0,001 |
| Parciais como falha | N2 × N3 | 4,44 | 2,45 a 8,04 | < 0,001 | < 0,001 |
| Inconclusivas como falha | N1 × N2 | 9,57 | 4,68 a 19,56 | < 0,001 | < 0,001 |
| Inconclusivas como falha | N1 × N3 | 12,05 | 6,26 a 23,21 | < 0,001 | < 0,001 |
| Inconclusivas como falha | N2 × N3 | 3,22 | 1,82 a 5,69 | < 0,001 | < 0,001 |
| Inconclusivas como aprovação | N1 × N2 | 31,00 | 9,99 a 96,16 | < 0,001 | < 0,001 |
| Inconclusivas como aprovação | N1 × N3 | não calculável | não calculável | < 0,001 | < 0,001 |
| Inconclusivas como aprovação | N2 × N3 | não calculável | não calculável | < 0,001 | < 0,001 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


### 4.4 QP3: atendimento funcional

Foram aprovadas funcionalmente 195 gerações em N0, 198 em N1, 192 em N2 e 180 em N3. Conforme a metodologia, o critério de N0 considera os requisitos informados nesse nível; a comparação pelo critério completo abrange N1, N2 e N3.

Pelo critério completo, N1 × N2 apresentou p ajustado de 0,480; N1 × N3, de 0,003; e N2 × N3, de 0,033. Na comparação restrita ao grupo base, N0 × N3 apresentou p ajustado de 0,004. Os demais contrastes do grupo base não tiveram estatística calculável.

Na T10, cinco das seis reprovações funcionais do GPT em N3 continham o uso de ip.is_site_local, atributo inexistente em IPv4Address. Duas dessas ocorrências foram reproduzidas em execução à parte. A sexta utilizava httpx.getaddrinfo, também inexistente.


Tabela 6 - QP3: critério funcional completo

| Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---:|---|---:|---:|
| N1 × N2 | não calculável | não calculável | 0,480 | 0,480 |
| N1 × N3 | não calculável | não calculável | 0,001 | 0,003 |
| N2 × N3 | 0,17 | 0,04 a 0,72 | 0,016 | 0,033 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


Tabela 7 - QP3: grupo funcional base

| Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---:|---|---:|---:|
| N0 × N1 | não calculável | não calculável | não calculável | não calculável |
| N0 × N2 | não calculável | não calculável | não calculável | não calculável |
| N0 × N3 | não calculável | não calculável | 0,004 | 0,004 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


### 4.5 Resultados por tarefa e modelo

A Tabela 8 apresenta contagens e intervalos de Wilson de 95% para as gerações com falha; o Apêndice A traz as proporções linha a linha. Cada célula corresponde a uma combinação de tarefa, modelo e nível. O denominador é o total de dez gerações da célula, incluindo as inconclusivas, diferentemente da proporção entre conclusivas da subseção 4.1. Gemini identifica gemini-3.8-flash, e GPT identifica gpt-5.4-mini-2026-03-17. T01 apresentou falha em todas as gerações de N0, N1 e N2 dos dois modelos. Em T07, esse padrão também ocorreu, exceto em uma geração de N1 do Gemini. T02 e T08 não apresentaram falhas observadas em nenhum nível. A ausência de falha nesta tabela não distingue aprovação, aprovação parcial e avaliação inconclusiva.

Na T03, com o critério corrigido, o Gemini apresentou dez falhas em N0, duas em N1 e nenhuma em N2 e N3; o GPT apresentou oito, uma, uma e nenhuma, respectivamente. Em T09 e T10, não houve falhas observadas em N2 ou N3 nos casos testados.


Tabela 8 - Falhas por célula: contagem e intervalo de Wilson de 95%, em pontos percentuais; critério corrigido

| Tarefa | Gemini N0 | Gemini N1 | Gemini N2 | Gemini N3 | GPT N0 | GPT N1 | GPT N2 | GPT N3 |
|---|---|---|---|---|---|---|---|---|
| T01 | 10/10 (72–100) | 10/10 (72–100) | 10/10 (72–100) | 0/10 (0–28) | 10/10 (72–100) | 10/10 (72–100) | 10/10 (72–100) | 0/10 (0–28) |
| T02 | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) |
| T03 | 10/10 (72–100) | 2/10 (6–51) | 0/10 (0–28) | 0/10 (0–28) | 8/10 (49–94) | 1/10 (2–40) | 1/10 (2–40) | 0/10 (0–28) |
| T04 | 2/10 (6–51) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) |
| T05 | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 5/10 (24–76) | 10/10 (72–100) | 1/10 (2–40) | 0/10 (0–28) |
| T06 | 0/10 (0–28) | 7/10 (40–89) | 0/10 (0–28) | 0/10 (0–28) | 5/10 (24–76) | 1/10 (2–40) | 0/10 (0–28) | 0/10 (0–28) |
| T07 | 10/10 (72–100) | 9/10 (60–98) | 10/10 (72–100) | 0/10 (0–28) | 10/10 (72–100) | 10/10 (72–100) | 10/10 (72–100) | 0/10 (0–28) |
| T08 | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) | 0/10 (0–28) |
| T09 | 10/10 (72–100) | 10/10 (72–100) | 0/10 (0–28) | 0/10 (0–28) | 3/10 (11–60) | 9/10 (60–98) | 0/10 (0–28) | 0/10 (0–28) |
| T10 | 10/10 (72–100) | 10/10 (72–100) | 0/10 (0–28) | 0/10 (0–28) | 10/10 (72–100) | 10/10 (72–100) | 0/10 (0–28) | 0/10 (0–28) |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


Os casos de limites numéricos excluídos do desfecho principal foram contabilizados separadamente. Cada linha reúne 20 gerações dos dois modelos. A coluna sem resultado ou não executado preserva as gerações sem avaliação do caso, sem tratá-las como aprovação.


Tabela 9 - Casos fora do desfecho principal

| Tarefa | Caso | Nível | Aprovado | Reprovado | Inconclusivo | Sem resultado ou não executado |
| --- | --- | --- | --- | --- | --- | --- |
| T03 | Excesso de bytes | N0 | 0 | 20 | 0 | 0 |
| T03 | Excesso de bytes | N1 | 0 | 20 | 0 | 0 |
| T03 | Excesso de bytes | N2 | 0 | 18 | 0 | 2 |
| T03 | Excesso de bytes | N3 | 20 | 0 | 0 | 0 |
| T03 | Excesso de dimensões | N0 | 0 | 20 | 0 | 0 |
| T03 | Excesso de dimensões | N1 | 0 | 20 | 0 | 0 |
| T03 | Excesso de dimensões | N2 | 0 | 18 | 0 | 2 |
| T03 | Excesso de dimensões | N3 | 20 | 0 | 0 | 0 |
| T05 | Validade aos 900 segundos | N0 | 1 | 19 | 0 | 0 |
| T05 | Validade aos 900 segundos | N1 | 0 | 20 | 0 | 0 |
| T05 | Validade aos 900 segundos | N2 | 9 | 11 | 0 | 0 |
| T05 | Validade aos 900 segundos | N3 | 19 | 0 | 0 | 1 |
| T05 | Validade aos 901 segundos | N0 | 2 | 18 | 0 | 0 |
| T05 | Validade aos 901 segundos | N1 | 0 | 20 | 0 | 0 |
| T05 | Validade aos 901 segundos | N2 | 16 | 4 | 0 | 0 |
| T05 | Validade aos 901 segundos | N3 | 19 | 0 | 0 | 1 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.

O caso expira_em_uma_semana, que integra o desfecho principal da T05, não reprovou em nenhuma das 80 gerações: houve 79 aprovações e uma geração sem resultado do caso, em N3.

### 4.6 Análise estática

Os achados do Bandit e do Semgrep foram contabilizados separadamente. A quantidade de achados pode superar a de gerações com achado, pois uma mesma resposta pode receber mais de um alerta. Esses indicadores descrevem alertas das ferramentas. A proporção corresponde às gerações com achado divididas pelo número de respostas com código submetidas à análise; a média corresponde ao total de achados dividido pelo mesmo denominador. Cada combinação reuniu 100 respostas, exceto no Bandit para o GPT em N3, com 99, porque uma resposta com erro de sintaxe não pôde ser analisada; esse erro não representa aprovação de segurança.


Tabela 10 - Proporção de gerações com achado e média de achados

| Ferramenta | Modelo | Nível | Analisadas | Com achado | Proporção | Achados | Média |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bandit | gemini-3.8-flash | N0 | 100 | 10 | 10,0% | 20 | 0,20 |
| bandit | gemini-3.8-flash | N1 | 100 | 10 | 10,0% | 20 | 0,20 |
| bandit | gemini-3.8-flash | N2 | 100 | 17 | 17,0% | 27 | 0,27 |
| bandit | gemini-3.8-flash | N3 | 100 | 12 | 12,0% | 22 | 0,22 |
| bandit | gpt-5.4-mini-2026-03-17 | N0 | 100 | 11 | 11,0% | 22 | 0,22 |
| bandit | gpt-5.4-mini-2026-03-17 | N1 | 100 | 12 | 12,0% | 22 | 0,22 |
| bandit | gpt-5.4-mini-2026-03-17 | N2 | 100 | 18 | 18,0% | 29 | 0,29 |
| bandit | gpt-5.4-mini-2026-03-17 | N3 | 99 | 15 | 15,2% | 25 | 0,25 |
| semgrep | gemini-3.8-flash | N0 | 100 | 10 | 10,0% | 10 | 0,10 |
| semgrep | gemini-3.8-flash | N1 | 100 | 10 | 10,0% | 10 | 0,10 |
| semgrep | gemini-3.8-flash | N2 | 100 | 10 | 10,0% | 10 | 0,10 |
| semgrep | gemini-3.8-flash | N3 | 100 | 10 | 10,0% | 10 | 0,10 |
| semgrep | gpt-5.4-mini-2026-03-17 | N0 | 100 | 12 | 12,0% | 12 | 0,12 |
| semgrep | gpt-5.4-mini-2026-03-17 | N1 | 100 | 15 | 15,0% | 15 | 0,15 |
| semgrep | gpt-5.4-mini-2026-03-17 | N2 | 100 | 5 | 5,0% | 5 | 0,05 |
| semgrep | gpt-5.4-mini-2026-03-17 | N3 | 100 | 19 | 19,0% | 19 | 0,19 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


No Bandit, foram registrados 160 achados associados à CWE-78, dez à CWE-20, oito à CWE-703, cinco à CWE-377, três à CWE-259 e um à CWE-89. No Semgrep, foram registrados 71 achados associados à CWE-78 e 20 à CWE-89. Nenhuma das duas ferramentas acusou CWE-79 ou CWE-918 nesta coleta. Houve um erro de análise no Bandit, na amostra com erro de sintaxe, e nenhum no Semgrep.

### 4.7 Revisão manual

A revisão foi feita pelo autor, com apoio de ferramenta de IA, em 80 gerações sem indicação de nível e modelo. Foram consideradas corretas 76 das 80 classificações registradas, antes da Emenda 02. Os quatro erros de classificação ocorreram na T03 e foram falsos positivos nos casos de extensão de arquivo. Separadamente, a inspeção identificou três falhas não detectadas pelos casos testados: uma omissão do delimitador de opções antes da categoria fornecida ao utilitário externo, na T07, de caráter potencial porque um erro de importação impedia a execução do código; e duas implementações da T10 que permitiam endereços da faixa não pública 100.64.0.0/10, não contemplada pelos testes. Essas três observações não compõem os quatro erros de classificação. Os 11 alertas estáticos presentes na amostra foram considerados falsos positivos.

A revisão também identificou o falso positivo nos casos de extensão da T03 que motivou a Emenda 02. O verificador registrado reprovava a resposta 2xx mesmo quando a aplicação substituía o nome recebido e gravava a imagem com extensão permitida.

### 4.8 Resultado registrado e resultado corrigido

A Emenda 02 alterou os casos extensao_dupla e extensao_html da T03. As 80 gerações da tarefa foram reavaliadas, e 33 tiveram mudança de reprovado para aprovado nesses casos. A classificação corrigida foi produzida depois de conhecidos os dados; os resultados registrados foram preservados.

No resultado registrado, as contagens de falhas foram 105 em N0, 114 em N1, 58 em N2 e zero em N3. Após a correção, passaram a 103, 99, 42 e zero. As contagens de aprovação funcional e de avaliações inconclusivas permaneceram iguais.


Tabela 11 - Classificação por nível: critério registrado

| Nível | Falha | Aprovada | Parcial | Inconclusiva | Falha entre conclusivas | Funcional aprovado |
|---|---:|---:|---:|---:|---:|---:|
| N0 | 105 | 71 | 17 | 7 | 54,4% | 195 |
| N1 | 114 | 63 | 20 | 3 | 57,9% | 198 |
| N2 | 58 | 126 | 10 | 6 | 29,9% | 192 |
| N3 | 0 | 166 | 16 | 18 | 0,0% | 180 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


Tabela 12 - Falhas e intervalos de Wilson na T03: critério registrado

| Tarefa | Modelo | Nível | Falhas/n | Proporção | IC 95% de Wilson |
|---|---|---|---|---|---|
| T03 | Gemini | N0 | 10/10 | 100,0% | 72,2% a 100,0% |
| T03 | Gemini | N1 | 10/10 | 100,0% | 72,2% a 100,0% |
| T03 | Gemini | N2 | 10/10 | 100,0% | 72,2% a 100,0% |
| T03 | Gemini | N3 | 0/10 | 0,0% | 0,0% a 27,8% |
| T03 | GPT | N0 | 10/10 | 100,0% | 72,2% a 100,0% |
| T03 | GPT | N1 | 8/10 | 80,0% | 49,0% a 94,3% |
| T03 | GPT | N2 | 7/10 | 70,0% | 39,7% a 89,2% |
| T03 | GPT | N3 | 0/10 | 0,0% | 0,0% a 27,8% |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.

Nas demais tarefas, as contagens registradas são idênticas às da Tabela 8.

Na QP1, a análise principal registrada apresentou p ajustado de 0,115, enquanto a corrigida apresentou 0,490. Na sensibilidade com aprovações parciais contadas como falha, o p ajustado passou de 0,023 para 0,889. Nas demais sensibilidades de QP1, ambas as versões apresentaram p ajustado superior a 0,05. Em QP2, os contrastes apresentaram p ajustado inferior a 0,001 nas duas versões, inclusive nas sensibilidades. Os resultados de QP3 não foram alterados.


Tabela 13 - Critério registrado, QP1: principal

| Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---:|---|---:|---:|
| N0 × N1 | 0,52 | 0,23 a 1,14 | 0,115 | 0,115 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


Tabela 14 - QP1 registrada: análises de sensibilidade

| Análise de sensibilidade | Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---|---:|---|---:|---:|
| Parciais como falha | N0 × N1 | 0,38 | 0,16 a 0,89 | 0,023 | 0,023 |
| Inconclusivas como falha | N0 × N1 | 0,72 | 0,35 a 1,46 | 0,441 | 0,441 |
| Inconclusivas como aprovação | N0 × N1 | 0,52 | 0,25 a 1,11 | 0,095 | 0,095 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


Tabela 15 - Critério registrado, QP2: principal

| Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---:|---|---:|---:|
| N1 × N2 | 36,57 | 10,94 a 122,24 | < 0,001 | < 0,001 |
| N1 × N3 | não calculável | não calculável | < 0,001 | < 0,001 |
| N2 × N3 | não calculável | não calculável | < 0,001 | < 0,001 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


Tabela 16 - QP2 registrada: análises de sensibilidade

| Análise de sensibilidade | Contraste | Razão de chances | IC 95% | p | p ajustado (Holm) |
|---|---|---:|---|---:|---:|
| Parciais como falha | N1 × N2 | 43,00 | 12,49 a 148,02 | < 0,001 | < 0,001 |
| Parciais como falha | N1 × N3 | 87,34 | 24,61 a 309,92 | < 0,001 | < 0,001 |
| Parciais como falha | N2 × N3 | 5,81 | 3,30 a 10,21 | < 0,001 | < 0,001 |
| Inconclusivas como falha | N1 × N2 | 10,81 | 5,08 a 23,01 | < 0,001 | < 0,001 |
| Inconclusivas como falha | N1 × N3 | 14,03 | 7,36 a 26,72 | < 0,001 | < 0,001 |
| Inconclusivas como falha | N2 × N3 | 4,41 | 2,58 a 7,53 | < 0,001 | < 0,001 |
| Inconclusivas como aprovação | N1 × N2 | 24,33 | 9,05 a 65,41 | < 0,001 | < 0,001 |
| Inconclusivas como aprovação | N1 × N3 | não calculável | não calculável | < 0,001 | < 0,001 |
| Inconclusivas como aprovação | N2 × N3 | não calculável | não calculável | < 0,001 | < 0,001 |

Fonte: elaborado pelo autor (2026), a partir dos dados da coleta principal.


