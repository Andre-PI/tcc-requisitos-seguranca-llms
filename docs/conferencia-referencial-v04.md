# Conferência do referencial e da ligação com a metodologia

Data: 3 de novembro de 2026.

## Escopo

Foram conferidos a estrutura e o texto da versão 3, as passagens das fontes que sustentam as afirmações mantidas e os metadados de publicação disponíveis. O trabalho resultou em referencial-v04.md. Esta foi uma conferência dirigida das afirmações utilizadas, não uma revisão sistemática nem uma declaração de leitura integral de todas as obras citadas.

O guia fornecido, baseado em Wazlawick, orientou a separação entre conceitos, pesquisas anteriores e contribuição pretendida. O livro de Wazlawick não foi incluído como fonte teórica lida. A referência institucional utilizada é o modelo de artigo de 2026 e o manual correspondente do repositório do coordenador, com origem registrada em origem-orientacoes-2026-11-03.json.

## Fontes e afirmações conferidas

| Fonte | Ponto utilizado no texto | Local de conferência |
|---|---|---|
| NASA | Requisitos claros, consistentes, verificáveis e rastreáveis | SWE-050, notas 1.1 e justificativa 2: https://swehb.nasa.gov/spaces/SWEHBVD/pages/102695421/SWE-050%2B-%2BSoftware%2BRequirements |
| MITRE | CWE como classificação de fraquezas | About CWE: https://cwe.mitre.org/about/index.html |
| OWASP | ASVS como referência de requisitos e verificação | Página oficial: https://owasp.org/projects/asvs; edição referenciada: 5.0.0 |
| Bandit | Uso de AST e verificadores para Python | Documentação oficial: https://bandit.readthedocs.io/en/latest/ |
| Semgrep | Regras, padrões e análise de fluxo | Documentação oficial: https://docs.semgrep.dev/writing-rules/overview |
| Pearce et al. | Dimensão do conjunto e proporção aproximada citada | Registro e resumo da versão 3: https://arxiv.org/abs/2108.09293v3 |
| Perry et al. | Estudo humano e contraste entre confiança e segurança | Registro e resumo da versão 3: https://arxiv.org/abs/2211.03622v3 |
| Khoury et al. | Geração e solicitação de melhorias | Registro e resumo da versão 2: https://arxiv.org/abs/2304.09655v2 |
| Tony et al. | Técnicas, conjunto, validade e descarte/regeneração | Resumo e seção 5.3.2 da versão 2: https://arxiv.org/html/2407.07064v2 |
| Kharma et al. | Modelos, métodos, revisão manual e conclusões | Resumo, apresentação do método e resultados da versão 1: https://arxiv.org/html/2605.24298v1 |
| Basic e Giaretta | Escopo da revisão e 102 estudos incluídos | Resumo e seção 3.4 da versão 4: https://arxiv.org/html/2412.15004v4 |
| Wang et al. | Testes funcionais, análise estática e adjudicação por modelos | Seções 4.2 e 4.3 da versão 1: https://arxiv.org/html/2601.22706v1 |
| Patir et al. | Avaliação conjunta e modelo como oráculo | Seções de avaliação e apêndice A.3 da versão 3: https://arxiv.org/html/2511.20709v3 |

Os metadados de quatro publicações foram obtidos diretamente dos registros Crossref associados aos DOIs e salvos em metadados-referencias-verificados.json. Confirmaram-se os anos e páginas de Pearce, Khoury e Perry e o volume 34, número 8, páginas 1-53 de Tony. A edição antecipada indicada por alguns repositórios institucionais divergia do número final; foi usado o registro de publicação do DOI.

## Correções de conteúdo

- Conceitos necessários à avaliação foram reunidos nas subseções 2.1 a 2.4. Os estudos anteriores foram concentrados em 2.5, com comparação no Quadro 1.
- A revisão identifica que Tony também inspeciona adequação funcional e completude. Assim, a diferença não é descrita como ausência absoluta de avaliação funcional, e sim como diferença de procedimento e tratamento das saídas inválidas.
- A descrição de RealSec-bench distingue testes funcionais, análise estática e revisão de alertas por modelos.
- DualGauge foi atualizado da versão 2 para a versão 3, de outubro de 2026, sem misturar números das duas versões.
- A contribuição foi vinculada ao recorte e às perguntas de pesquisa. A combinação de segurança e funcionalidade não foi apresentada como inédita.
- N1 permanece como base funcional, com reconhecimento do efeito concorrente da extensão textual.
- As chamadas e a lista de referências foram revistas para manter correspondência. A nova fonte sobre Semgrep foi acrescentada porque o instrumento integra a metodologia.

## Correspondência com a metodologia v04

| Elemento do referencial | Aplicação metodológica |
|---|---|
| Detalhamento e exigência de segurança | N0 a N3; contrastes das QP1 e QP2 |
| Verificabilidade dos requisitos | Critérios e controles dos testes |
| CWE e ASVS | Classificação das fraquezas e elaboração dos requisitos; mapeamento ASVS ainda pendente |
| Correção e oráculo funcional | Capacidades mínimas e contrato detalhado; cálculo das expectativas |
| Análise estática e verificação comportamental | Instrumentos complementares; resultado por propriedade |
| Falha funcional e avaliação inconclusiva | Categorias e denominadores em 3.5 |
| Avaliação conjunta | Relação entre aprovação funcional e propriedades de segurança examinadas |

O Quadro 1 está no referencial. Os Quadros 2, 3 e 4 estão na metodologia v04. A sequência é contínua quando as seções são integradas. Não foram alterados prompts, códigos gerados, registros de execução ou resultados do piloto para produzir esta revisão.

## Alcance da adequação

O texto segue a função das seções descrita no guia, e os documentos parciais mantêm a formatação básica expressa no manual institucional. A identidade visual e a compilação do projeto LaTeX do coordenador pertencem à montagem final do artigo; os PDFs parciais não são apresentados como uma compilação desse template. A revisão do orientador e a revisão profissional de português exigida pelo manual continuam sendo etapas distintas desta conferência.
