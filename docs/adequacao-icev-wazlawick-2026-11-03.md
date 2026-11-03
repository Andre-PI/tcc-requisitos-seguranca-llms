# Adequação às orientações recebidas em 3 de novembro de 2026

## Materiais efetivamente consultados

1. Repositório indicado pelo coordenador: https://github.com/dimmykarson/modelo-icev-esw. Foi baixada uma cópia em normas/modelo-icev-esw. Utilizados README, modelo LaTeX de artigo de 2026, PDF de exemplo, modelo Word original e páginas pertinentes do manual de 2026. O modelo de 2023 não foi adotado.
2. Guia_Escrita_Artigo_Wazlawick.pdf, nove páginas, fornecido pelo usuário e copiado dos Downloads para normas. O guia se apresenta como material baseado na terceira edição do livro de Wazlawick. A leitura do guia não equivale à leitura integral do livro, que não foi feita nesta etapa.

O manual de 2026 mantém, nas páginas físicas 7, 8 e 13, o mínimo de 20 laudas, a revisão por profissional de Letras e a formatação básica já utilizada. O modelo LaTeX do coordenador acrescenta apresentação visual com marca do iCEV, títulos de seção em 18 pontos e paginação inferior. O corpo permanece em fonte serifada de 12 pontos. Essas opções do modelo não significam que todo artigo deva ser escrito em LaTeX.

## O que foi ajustado

| Orientação do guia | Tratamento na versão 4 da metodologia |
|---|---|
| Explicitar questões ou hipóteses | QP1, QP2 e QP3 em 3.1 |
| Definir variáveis | Nível manipulado, respostas e fatores de agrupamento em 3.2 |
| Relacionar comparações às perguntas | Quadro 2 |
| Explicar o cálculo das métricas | Fórmulas e denominadores em 3.5 |
| Definir sucesso, erro e impedimento | Quadro 4 e controles positivos em 3.4 |
| Distinguir método e implementação | Descrição dos critérios no artigo; detalhes dos scripts no repositório |
| Explicitar limitações | Subsecção 3.6 |
| Distinguir executado e planejado | Piloto descrito nas subseções 3.1 a 3.6; coleta principal em 3.7 |

A versão anterior não foi descartada. Seu conteúdo técnico continua como base de reprodução, mas a nova redação concentra o método na relação entre pergunta, medida e evidência. A formulação explícita de perguntas e fórmulas é uma organização atual dos critérios; não deve ser apresentada como pré-registro de setembro.

## O que ainda falta para fechar o desenho principal

Escolher o segundo modelo/provedor; definir contratos e versões informados em cada nível; obter e arquivar as regras estáticas antes das novas análises; registrar o plano de comparação estatística; construir verificadores das sete tarefas restantes; estabelecer isolamento adequado para tarefas com efeitos externos; planejar revisão humana independente. Esses itens não impedem avançar no desenvolvimento, mas precisam estar resolvidos antes da coleta que usará o protocolo correspondente.

O primeiro passo técnico será implementar uma tarefa adicional e conferir o instrumento com código de referência correto e com falhas conhecidas. Sugestão inicial: T04, download de arquivo por nome, para testar travessia de diretórios e preservação da função de download em um ambiente temporário controlado. Isso não autoriza executar código gerado sem isolamento.

## Estrutura de escrita

Manter uma seção de referencial com conceitos e uma subseção própria de trabalhos relacionados. A metodologia explicará o desenho e os critérios; a execução do piloto terá sua descrição concreta; resultados e discussão ficarão distintos. O guia permite organizar esses componentes como subseções do desenvolvimento: não exige transformar cada rótulo em um capítulo separado. Resumo e abstract serão finalizados após as análises. A introdução existente continua como rascunho a revisar quando o escopo estiver consolidado.

O planejamento permanece em 800 gerações. A ampliação será precedida pela validação dos instrumentos, sem antecipação de resultados ou garantia de significância estatística pelo tamanho da coleta.
