## 3 METODOLOGIA

### 3.1 Delineamento e questões de pesquisa

O estudo compara código Python/FastAPI gerado por modelos de linguagem sob quatro condições de especificação de requisitos. A avaliação é quantitativa e examina separadamente a correção funcional e as propriedades de segurança selecionadas para cada tarefa. A investigação de falhas de execução complementa as medidas, distinguindo problemas do código gerado, incompatibilidades com o ambiente informado e defeitos dos instrumentos de avaliação.

A investigação é orientada por três questões. QP1: como o detalhamento funcional se relaciona com as falhas de segurança observadas? QP2: o acréscimo de orientações genéricas ou de requisitos específicos de segurança altera a frequência e os tipos de falhas? QP3: como a aprovação funcional varia entre essas condições? A terceira questão permite examinar uma possível perda funcional associada à especificação de segurança, sem pressupor sua ocorrência.

A pesquisa compreende três etapas: um piloto com 72 gerações em três tarefas; coletas exploratórias destinadas à construção e revisão dos instrumentos; e uma coleta principal planejada com dez tarefas, quatro níveis, dois modelos e dez repetições por combinação, totalizando 800 novas gerações. Os registros do piloto e das coletas exploratórias são preservados separadamente da amostra principal. As coletas com uma geração por condição permitem identificar problemas do procedimento, mas não sustentam conclusões sobre diferenças entre níveis ou modelos.

Cada geração constitui uma unidade de análise. Os casos de teste são observações sobre essa unidade e não aumentam o tamanho da amostra de gerações. As comparações previstas consideram tarefa e modelo como fatores de agrupamento. O desenho compara quatro condições de especificação; não corresponde ao cruzamento completo de dois fatores independentes de detalhamento funcional e segurança. O plano estatístico da etapa principal permanece pendente e deverá ser registrado antes de sua execução.

### 3.2 Variáveis e condições de comparação

A variável manipulada é o nível da especificação. Na versão revisada do procedimento, cada prompt reúne o enunciado correspondente ao nível, um contrato de integração comum aos quatro níveis daquela tarefa e a instrução de responder somente com código Python.

N0 contém uma solicitação funcional breve acrescida do contrato comum. N1 apresenta a descrição funcional detalhada e o mesmo contrato. N2 mantém N1 e acrescenta uma orientação genérica de boas práticas e diretrizes do OWASP. N3 mantém N1 e acrescenta requisitos específicos de segurança. N2 e N3 são extensões alternativas de N1; N3 não é construído pelo acréscimo de requisitos ao texto de N2.

O contrato comum estabelece as interfaces e as condições necessárias à execução: módulo e instância da aplicação, rotas, campos de entrada, formatos de resposta, esquema de banco quando aplicável, variáveis de ambiente, colaboradores fornecidos e versões declaradas. Sua finalidade é permitir que as respostas sejam submetidas aos testes sem adaptações posteriores de interface. A regra adotada procura reservar as instruções de proteção ao complemento de N3. Entretanto, a informação sobre o ambiente e as interfaces também pode influenciar a solução, e esse efeito constitui uma limitação do desenho.

Assim, N0 representa uma especificação breve dentro de uma interface previamente definida. A comparação entre N0 e N1 examina o detalhamento adicional ao contrato, cujo conteúdo já fornece parte dos requisitos funcionais a todos os níveis. Essa definição difere da condição do piloto, na qual as respostas podiam exigir adaptações de interface. Os resultados das duas etapas não serão combinados como observações de uma mesma condição experimental.

Na T06, o contrato informa a coluna que identifica o proprietário do pedido e disponibiliza uma dependência que retorna o usuário autenticado. Essas informações permitem avaliar autorização sobre uma identidade controlada, mas também podem sugerir a verificação de propriedade e reduzir a diferença entre N0 e N1. A manutenção desse contrato é uma decisão provisória a ser discutida com o orientador antes da coleta principal. Na T01, a inclusão de uma rota de registro permite observar o armazenamento da senha e amplia o escopo em relação ao login isolado do piloto.

Quadro 2 - Relação entre questões e comparações previstas

| Questão | Comparações | Medidas observadas |
|---|---|---|
| QP1 | N0 e N1, por tarefa e modelo | Achados estáticos e falhas comportamentais por propriedade, considerando as informações já presentes no contrato comum |
| QP2 | N1 e N2; N1 e N3; N2 e N3 | Frequência de falhas observadas e categorias CWE |
| QP3 | N0 a N3, com critérios funcionais associados aos requisitos informados | Aprovação funcional, reprovação e avaliação inconclusiva |

Fonte: elaborado pelo autor (2026).

As variáveis de resposta são a presença e a contagem de achados estáticos, as categorias CWE atribuídas, os resultados comportamentais por propriedade e o atendimento funcional por grupo de testes. Versões de bibliotecas, parâmetros de geração, ordem das chamadas e configuração dos verificadores são condições de execução a registrar. Uma falha que impeça o controle funcional pode tornar inconclusiva a avaliação de segurança; a ausência de execução não será interpretada como ausência de vulnerabilidade.

Nos instrumentos revisados de T03, T04, T07, T08, T09 e T10, os casos funcionais são divididos em base e detalhado. O grupo base verifica a operação necessária à avaliação de segurança. O grupo detalhado reúne capacidades solicitadas a partir de N1 e é registrado separadamente, sem bloquear essa avaliação. Em N0, a ausência dessas capacidades não reprova o atendimento aos requisitos informados; em N1, N2 e N3, elas integram o critério funcional. Uma falha de segurança observada continua sendo registrada mesmo quando o controle base falha. A classificação dos casos e sua incorporação ao executor deverão estar fechadas antes da coleta principal.
