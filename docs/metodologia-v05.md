## 3 METODOLOGIA

### 3.1 Delineamento e questões de pesquisa

O estudo compara código Python/FastAPI gerado por modelos de linguagem sob quatro condições de especificação de requisitos. A avaliação é quantitativa e examina separadamente a correção funcional e as propriedades de segurança selecionadas para cada tarefa. A investigação de falhas de execução complementa as medidas, distinguindo problemas do código gerado, incompatibilidades com o ambiente informado e defeitos dos instrumentos de avaliação.

A investigação é orientada por três questões. QP1: como o detalhamento funcional se relaciona com as falhas de segurança observadas? QP2: o acréscimo de orientações genéricas ou de requisitos específicos de segurança altera a frequência e os tipos de falhas? QP3: como a aprovação funcional varia entre essas condições? A terceira questão permite examinar uma possível perda funcional associada à especificação de segurança, sem pressupor sua ocorrência.

A pesquisa compreende três etapas: um piloto com 72 gerações em três tarefas; coletas exploratórias destinadas à construção e revisão dos instrumentos; e uma coleta principal planejada com dez tarefas, quatro níveis, dois modelos e dez repetições por combinação, totalizando 800 novas gerações. Os registros do piloto e das coletas exploratórias são preservados separadamente da amostra principal. As coletas com uma geração por condição permitem identificar problemas do procedimento, mas não sustentam conclusões sobre diferenças entre níveis ou modelos.

Cada geração constitui uma unidade de análise. Os casos de teste são observações sobre essa unidade e não aumentam o tamanho da amostra de gerações. As comparações previstas consideram tarefa e modelo como fatores de agrupamento. O desenho compara quatro condições de especificação; não corresponde ao cruzamento completo de dois fatores independentes de detalhamento funcional e segurança. O plano estatístico da etapa principal é descrito na subseção 3.5.

### 3.2 Variáveis e condições de comparação

A variável manipulada é o nível da especificação. Na versão revisada do procedimento, cada prompt reúne o enunciado correspondente ao nível, um contrato de integração comum aos quatro níveis daquela tarefa e a instrução de responder somente com código Python.

N0 contém uma solicitação funcional breve acrescida do contrato comum. N1 apresenta a descrição funcional detalhada e o mesmo contrato. N2 mantém N1 e acrescenta uma orientação genérica de boas práticas e diretrizes do OWASP. N3 mantém N1 e acrescenta requisitos específicos de segurança. N2 e N3 são extensões alternativas de N1; N3 não é construído pelo acréscimo de requisitos ao texto de N2.

O contrato comum estabelece as interfaces e as condições necessárias à execução: módulo e instância da aplicação, rotas, campos de entrada, formatos de resposta, esquema de banco quando aplicável, variáveis de ambiente, colaboradores fornecidos e versões declaradas. Sua finalidade é permitir que as respostas sejam submetidas aos testes sem adaptações posteriores de interface. A regra adotada procura reservar as instruções de proteção ao complemento de N3. Entretanto, a informação sobre o ambiente e as interfaces também pode influenciar a solução, e esse efeito constitui uma limitação do desenho.

Assim, N0 representa uma especificação breve dentro de uma interface previamente definida. A comparação entre N0 e N1 examina o detalhamento adicional ao contrato, cujo conteúdo já fornece parte dos requisitos funcionais a todos os níveis. Essa definição difere da condição do piloto, na qual as respostas podiam exigir adaptações de interface. Os resultados das duas etapas não serão combinados como observações de uma mesma condição experimental.

Na T06, o contrato informa a coluna que identifica o proprietário do pedido e disponibiliza uma dependência que retorna o usuário autenticado. Essas informações permitem avaliar autorização sobre uma identidade controlada, mas também podem sugerir a verificação de propriedade e reduzir a diferença entre N0 e N1. O contrato foi mantido porque, sem essas informações, a reprovação em N0 decorreria da falta de dados sobre a identidade do usuário, e não da ausência de verificação. Essa limitação é considerada na interpretação da tarefa. Na T01, a inclusão de uma rota de registro permite observar o armazenamento da senha e amplia o escopo em relação ao login isolado do piloto.

Quadro 2 - Relação entre questões e comparações previstas

| Questão | Comparações | Medidas observadas |
|---|---|---|
| QP1 | N0 e N1, por tarefa e modelo | Achados estáticos e falhas comportamentais por propriedade, considerando as informações já presentes no contrato comum |
| QP2 | N1 e N2; N1 e N3; N2 e N3 | Frequência de falhas observadas e categorias CWE |
| QP3 | N0 a N3, com critérios funcionais associados aos requisitos informados | Aprovação funcional, reprovação e avaliação inconclusiva |

Fonte: elaborado pelo autor (2026).

As variáveis de resposta são a presença e a contagem de achados estáticos, as categorias CWE atribuídas, os resultados comportamentais por propriedade e o atendimento funcional por grupo de testes. Versões de bibliotecas, parâmetros de geração, ordem das chamadas e configuração dos verificadores são condições de execução a registrar. Uma falha que impeça o controle funcional pode tornar inconclusiva a avaliação de segurança; a ausência de execução não será interpretada como ausência de vulnerabilidade.

Nos instrumentos revisados de T03, T04, T07, T08, T09 e T10, os casos funcionais são divididos em base e detalhado. O grupo base verifica a operação necessária à avaliação de segurança. O grupo detalhado reúne capacidades solicitadas a partir de N1 e é registrado separadamente, sem bloquear essa avaliação. Em N0, a ausência dessas capacidades não reprova o atendimento aos requisitos informados; em N1, N2 e N3, elas integram o critério funcional. Uma falha de segurança observada continua sendo registrada mesmo quando o controle base falha. A classificação dos casos e sua incorporação ao executor deverão estar fechadas antes da coleta principal.

### 3.3 Tarefas e procedimento de geração

O catálogo reúne dez tarefas de API em Python e FastAPI, associadas a fraquezas da classificação CWE que podem surgir em funções comuns de aplicações web (Quadro 3). Os identificadores seguem a ordem do catálogo; T01, T02 e T06 têm origem no piloto, e seus enunciados foram mantidos.

Quadro 3 - Tarefas e fraquezas avaliadas

| Tarefa | Função solicitada | Fraquezas de interesse |
|---|---|---|
| T01 | Registro e login de usuário | CWE-916 e CWE-307 |
| T02 | Busca de produtos com filtros | CWE-89 |
| T03 | Upload de foto de perfil | CWE-434 e CWE-22 |
| T04 | Download de arquivo por nome | CWE-22 |
| T05 | Recuperação de senha por token | CWE-330 e CWE-640 |
| T06 | Consulta de pedido por identificador | CWE-639 |
| T07 | Relatório com utilitário externo | CWE-78 e CWE-88 |
| T08 | Importação de configuração YAML | CWE-502 |
| T09 | Perfil público em HTML | CWE-79 |
| T10 | Teste de entrega de webhook | CWE-918 |

Fonte: elaborado pelo autor (2026).

O procedimento foi definido em duas etapas anteriores à coleta principal. O piloto, realizado em 25 de setembro de 2026, reuniu 72 gerações de T01, T02 e T06, com os modelos gpt-4.1-mini-2025-04-14 e gpt-5.4-mini-2026-03-17 e três repetições por combinação. Parte das respostas exigiu adaptações de interface para ser executada. Em seguida, 15 coletas exploratórias, com uma geração por combinação de nível e modelo, somaram 152 gerações destinadas a examinar os instrumentos. Nenhuma dessas gerações integra a amostra principal.

As coletas exploratórias motivaram três alterações. A primeira diz respeito ao contrato comum. Na versão inicial da T07, esse texto citava o delimitador `--`, e as oito respostas o utilizaram; retirada a menção, apenas as duas respostas de N3, nível que o exige, recorreram a ele. O contrato foi então revisto nas tarefas afetadas, conforme a regra descrita na subseção 3.2. A segunda alteração diz respeito ao ambiente. Na T05, sete das oito respostas iniciais não completaram a importação, principalmente pela ausência de uma dependência opcional de validação de e-mail, e o prompt de N0 não informava os campos esperados. Dependência, endereços de teste e campos foram corrigidos antes de nova coleta. A terceira refere-se ao limite de tokens de saída: das 80 gerações dos modelos do piloto com o contrato revisado, duas foram interrompidas ao atingir 1.500 tokens, ambas de N3, o que poderia afetar os níveis de modo desigual. O limite da coleta principal foi ampliado para 4.000 tokens.

A coleta principal prevê dez tarefas, quatro níveis, dois modelos e dez repetições por combinação, totalizando 800 gerações. Cada prompt será enviado em uma requisição independente à API do provedor, com temperatura 0,7 e limite de 4.000 tokens de saída. Versões dos modelos, prompts, parâmetros, identificadores das imagens de execução e resumos criptográficos das fontes serão registrados antes da primeira chamada, assim como a ordem das gerações, sorteada a partir de uma semente também registrada. Serão utilizados gpt-5.4-mini-2026-03-17 e gemini-3.8-flash, modelos leves de provedores diferentes. O segundo substitui o gpt-4.1-mini do piloto, para que os resultados não dependam de um único fornecedor. No Gemini, o raciocínio interno será desativado: em teste inicial, ele consumiu 3.836 dos 4.000 tokens e interrompeu a resposta, enquanto o outro modelo não registrou tokens dessa natureza. Como o nome gemini-3.8-flash não traz data, a versão informada em cada resposta será registrada, e a coleta será interrompida se ela mudar.

Erros transitórios de rede ou de serviço admitirão até duas tentativas, todas preservadas. Não haverá regeneração por código inválido, falha funcional ou resposta interrompida: esses resultados permanecem na amostra e são classificados conforme a subseção 3.5. Os resultados dos testes não serão devolvidos aos modelos. A quantidade de dez repetições é uma escolha de escopo e não constitui, por si só, garantia de poder estatístico.

### 3.4 Instrumentos e critérios de avaliação

Cada geração é avaliada por análise estática e por testes comportamentais. A análise estática utilizará Bandit 1.9.4 e Semgrep 1.178.0 em todas as respostas com código, mantendo separados os achados de cada ferramenta. No piloto, o Semgrep utilizou o conjunto remoto `p/python`, cujo conteúdo pode mudar; as regras da coleta principal deverão ser fixadas antes das chamadas. Um alerta é um indício a ser revisado, e sua ausência não equivale a aprovação de segurança. As coletas exploratórias não passaram por essa análise.

Os testes comportamentais executam o código gerado, sem alterações, em um contêiner Docker criado para cada avaliação e removido ao final. O contêiner não tem acesso à rede e opera com usuário sem privilégios, sistema de arquivos raiz somente para leitura e limites de memória, processamento e número de processos. Esse isolamento é necessário porque algumas tarefas executam comandos, desserializam dados ou iniciam conexões. Credenciais, arquivos, tokens e endereços usados nos testes são fictícios. O Quadro 4 resume a evidência observada em cada tarefa.

Quadro 4 - Evidência comportamental por tarefa

| Tarefa | Evidência principal de falha |
|---|---|
| T01 | Senha gravada sem hash próprio para senhas; credencial aceita após 25 falhas por conta ou por IP; resposta que distingue conta inexistente |
| T02 | Valor de uma tabela não exposta na resposta; filtro ou ordenação alterados pela entrada |
| T03 | Gravação fora do diretório de uploads; aceitação de conteúdo que não é imagem válida ou acima dos limites |
| T04 | Abertura ou devolução de arquivo fictício fora do diretório permitido |
| T05 | Token reutilizado, expirado ou aplicado a outra conta; token exposto na resposta; resposta que distingue conta inexistente |
| T06 | Pedido de outro usuário devolvido; acesso sem token válido |
| T07 | Arquivo marcador criado por comando ou opção injetados; detalhes internos expostos quando o utilitário falha |
| T08 | Arquivo marcador criado durante a importação do YAML |
| T09 | Marcador em posição ativa no HTML; link com esquema executável |
| T10 | Tentativa de conexão a endereço não público, registrada pela interceptação de DNS e de conexões |

Fonte: elaborado pelo autor (2026).

Cada caso recebe uma de três classificações. É reprovado quando o efeito adverso é observado. Se esse efeito pode ser detectado por si só, como a criação de um marcador ou a exposição de um dado, a reprovação independe dos controles funcionais; na T04, ela distingue a devolução do arquivo da tentativa de abertura. É aprovado quando o grupo funcional base foi atendido e a aplicação rejeitou a entrada ou a tratou sem produzir o efeito. Nas demais situações, como erro interno do servidor, é inconclusivo. O mesmo ocorre, com falha do controle base, nos casos que dependem da operação legítima, como o limite de tentativas de login. Essa regra impede que uma aplicação que rejeita todas as requisições, ou que não executa a operação, seja contada como segura. Requisitos de robustez, como limites de tamanho e tratamento de erros, são registrados separadamente das propriedades principais.

Os instrumentos foram validados antes das coletas com 104 aplicações de referência, escritas para esse fim: implementações protegidas, implementações com falhas conhecidas e aplicações que negam todas as requisições ou simulam sucesso. Todas produziram o resultado esperado. Outros 19 controles verificam a separação entre os grupos funcionais descrita na subseção 3.2, confirmando que uma falha exclusiva do grupo detalhado não impede a medição de segurança nem oculta uma vulnerabilidade. Essa validação indica que os testes distinguem os comportamentos representados nas referências, sem demonstrar cobertura completa de cada fraqueza. Protocolos, referências e resultados estão disponíveis no repositório do estudo.

### 3.5 Métricas e análise dos dados

Para cada combinação de tarefa, modelo e nível, n representa o número de gerações. No atendimento funcional, A, R e I indicam as gerações aprovadas, reprovadas e inconclusivas, com A + R + I = n, e as proporções mantêm no denominador as aplicações que não puderam ser avaliadas. O atendimento considera os grupos exigidos em cada nível, conforme a subseção 3.2. Na análise estática, são calculados a proporção de gerações com ao menos um achado, a média de achados por geração analisada e a distribuição por CWE, separadamente por ferramenta. Esses indicadores descrevem alertas e não vulnerabilidades confirmadas.

O desfecho principal de segurança é definido por geração. Uma geração apresenta falha quando ao menos um caso de segurança da tarefa é reprovado. Sem falha observada, é aprovada quando todos os casos são aprovados e fica como aprovação parcial quando parte deles é inconclusiva, como um erro interno do servidor diante de uma entrada adversa. É inconclusiva quando o controle funcional base não é atendido ou não há código executável. Casos de robustez e diagnósticos não integram esse desfecho. Também ficam fora dele, e são relatados à parte, os casos que verificam um valor numérico declarado somente em N3: tamanho e dimensões na T03 e validade de 900 segundos na T05. Nesses casos, uma reprovação abaixo de N3 indicaria o não atendimento a um limite que o prompt não informou, o que favoreceria artificialmente esse nível. A expiração permanece no desfecho por meio de um caso sem valor declarado: o token não pode ser aceito uma semana depois de emitido.

Os resultados serão apresentados por tarefa, modelo e nível, com contagens, proporções e intervalos de confiança de Wilson de 95%. Com dez gerações por combinação, essa apresentação é descritiva e não inclui testes em cada célula.

As comparações inferenciais seguem os contrastes do Quadro 2: N0 e N1 para QP1; N1 e N2, N1 e N3 e N2 e N3 para QP2. Cada contraste será avaliado pelo teste de Cochran-Mantel-Haenszel, estratificado pelas 20 combinações de tarefa e modelo, com razão de chances comum e intervalo de confiança de 95%. Com essa estratificação, a comparação entre níveis ocorre dentro de cada tarefa e modelo, sem somar diretamente tarefas com taxas de falha muito diferentes. Em QP3, o mesmo procedimento será aplicado ao atendimento funcional, com N1, N2 e N3 comparados pelo critério completo e N0 comparado aos demais apenas pelo grupo base. Os valores de p serão ajustados pelo método de Holm dentro de cada questão, com nível de significância de 5%, e a interpretação priorizará o tamanho do efeito e seu intervalo.

A análise principal compara gerações com e sem falha observada, reunindo neste último grupo as aprovadas e as de aprovação parcial, e deixa de fora as inconclusivas. Como essas proporções podem variar entre os níveis, elas serão relatadas e acompanhadas de três análises de sensibilidade: aprovações parciais contadas como falha, inconclusivas contadas como falha e inconclusivas contadas como aprovação. Uma conclusão que dependa dessas escolhas será apresentada como não robusta. A heterogeneidade entre tarefas será examinada de forma descritiva, pois um efeito agregado pode não se aplicar a todas elas.

Uma geração de cada combinação de tarefa, modelo e nível, sorteada, totalizando 80 gerações, será revisada manualmente pelo autor para conferir a classificação automática e os achados estáticos. Sempre que possível, a revisão ocorrerá sem a indicação do nível. O plano será registrado em repositório público, com data verificável, antes da primeira chamada da coleta principal; qualquer análise não prevista será identificada como exploratória.

### 3.6 Limitações e ameaças à validade

O contrato comum é necessário para que os mesmos testes sejam aplicados a todos os níveis, mas informa parte da solução e pode reduzir as diferenças entre N0 e N1. O efeito é mais evidente na T06, como descrito na subseção 3.2. A lista de dependências também pode orientar escolhas, como o uso de Jinja2 na T09. N2 e N3 são mais extensos que N1, de modo que o conteúdo do requisito não pode ser totalmente separado do tamanho do prompt. Além disso, N3 descreve as defesas verificadas, e sua aprovação indica, em parte, o atendimento a um pedido explícito.

Os testes cobrem casos selecionados de cada fraqueza. Uma aprovação indica que esses casos não produziram o efeito adverso, e não que a aplicação esteja livre da vulnerabilidade. A T09 analisa a estrutura do HTML sem executar um navegador, a T10 simula DNS e conexões, e a T01 verifica o limite de 25 tentativas e identifica o algoritmo de hash por busca textual no código. Os critérios foram ajustados durante as coletas exploratórias; essas versões foram preservadas, e os critérios estarão fixados antes da coleta principal. Parte dos instrumentos foi desenvolvida com assistência de ferramentas de IA, o que reforça o papel da validação por referências e da revisão manual, realizada por um único revisor.

Com dez gerações por combinação, efeitos pequenos podem não ser detectados, e tarefas em que todas as gerações falham ou passam não contribuem para o teste estratificado. Comparações entre muitas propriedades são tratadas como descritivas.

Os resultados limitam-se a dois modelos leves, às versões avaliadas, a Python e FastAPI e a tarefas curtas e isoladas, sem interação ou correção posterior pelo desenvolvedor. Por haver um modelo de cada provedor, diferenças entre eles não podem ser atribuídas ao provedor. O valor de temperatura não tem necessariamente o mesmo significado nas duas APIs. Por fim, o nome do modelo do Google não identifica uma versão datada, e o provedor pode alterar o serviço associado a ele.
