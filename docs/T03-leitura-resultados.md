# T03 — leitura da coleta exploratória

A coleta reuniu oito respostas completas, obtidas em oito requisições, com consumo registrado de 7.274 tokens de entrada e saída somados. Não houve regeneração por falha funcional nem resposta truncada. O plano foi gravado antes da primeira chamada, com ordem sorteada, prompts, parâmetros, hashes das fontes e identificador da imagem Linux. Os dados estão em [t03-exploratoria](../dados/t03-exploratoria), separados do piloto e da coleta principal.

## Resultado observado

Seis amostras passaram nos três uploads legítimos. A amostra `t03-02` retornou 500 nos três casos. A amostra `t03-04` não importou, com `ModuleNotFoundError` para `imghdr` no Python 3.14.2. Nenhuma delas foi corrigida ou substituída.

As cinco amostras executáveis de N0, N1 e N2 aceitaram imagens válidas enviadas com extensão HTML ou dupla, conteúdo acima de 2 MiB e dimensão superior ao limite especificado em N3. Esses quatro critérios foram reprovados em cada uma. A aceitação de uma extensão de entrada não comprova execução de arquivo perigoso, sobretudo quando o servidor recodifica a imagem e atribui outra extensão ao arquivo salvo. Os resultados devem ser lidos como atendimento dos requisitos testados, sem equiparar cada reprovação a uma vulnerabilidade explorável.

A amostra `t03-07`, N3 de gpt-5.4-mini-2026-03-17, passou nos três uploads legítimos e nos 13 casos de segurança, além da ausência do campo e da preservação de envios com nomes repetidos. Isso demonstra atendimento aos casos executados, sem comprovar proteção completa contra uploads maliciosos ou esgotamento de recursos.

Não houve escrita externa observada nas seis amostras com controles funcionais aprovados. Nas outras duas, a execução não permite concluir proteção. Os resultados por caso, inclusive as evidências de abertura para escrita e as sentinelas, permanecem nos arquivos de avaliação.

## Diagnóstico inicial

Na `t03-02`, a inspeção do código identificou `Image.open(io := None)` antes da criação do `BytesIO`. Esse trecho é compatível com os erros 500 observados. Trata-se de um diagnóstico por inspeção; o relatório principal registra o efeito HTTP e não uma exceção interna comprovada por traceback.

Na `t03-04`, o executor registrou diretamente a falha de importação. O uso de um módulo indisponível no ambiente fixado é um problema de compatibilidade, cuja presença não pode ser atribuída automaticamente ao nível de segurança do prompt.

## Consequências para o protocolo

O fluxo de coleta e execução funcionou, e preservou também os resultados desfavoráveis. A separação entre capacidades funcionais, contrato, integridade e requisitos de segurança permite observar falhas distintas. Entretanto, uma repetição por combinação não sustenta comparação estatística ou conclusão sobre superioridade de modelo.

Antes da coleta principal, ainda é necessário revisar os critérios da T03, padronizar as interfaces entre as tarefas e validar os cinco instrumentos restantes. Deve ser explicitado no artigo que N0 recebe um contrato comum de integração e que os requisitos adicionais são usados como critérios de segurança em todos os níveis. A exigência de validação antes da gravação é observada na pasta de uploads, sem confundi-la com o armazenamento temporário interno do parser multipart.

O texto parcial dos resultados do piloto permanece referente às 72 gerações originais e à ampliação T04 que já estava documentada naquela versão. Esta coleta é um documento adicional; não altera os denominadores daquele texto.
