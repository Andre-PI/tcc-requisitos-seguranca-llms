# Emenda 02: critério de extensão na T03

Desvio do [plano da coleta principal](plano-coleta-principal.md), registrado em 4 de novembro de 2026, depois da coleta e da primeira análise.

## Defeito

Os casos `extensao_dupla` e `extensao_html` da T03 enviam uma imagem PNG válida com os nomes `foto.jpg.php` e `foto.html`. A versão registrada do verificador reprovava qualquer resposta 2xx, sem examinar o arquivo gravado. Assim, uma aplicação que descartava esse nome e gravava `<uuid>.png` era contada como falha, embora a extensão perigosa não tivesse sido preservada.

O problema foi identificado na revisão manual, em uma amostra de oito gerações da tarefa, e depois medido nas 80 gerações da T03, ou seja, já com conhecimento dos resultados da análise registrada.

## Correção

O verificador v5, em `instrumentos_v5/`, altera somente esses dois casos. Uma resposta 2xx passa a ser reprovada se o arquivo for gravado com extensão diferente de `.png`, `.jpg` ou `.jpeg`, e aprovada se a extensão for uma delas, atendidas as demais condições. As 80 gerações foram reavaliadas sem novas chamadas a modelos. O procedimento recusaria o resultado se qualquer outro caso mudasse.

A validação repetiu as nove referências e os quatro controles anteriores e acrescentou três controles: gravar com nome gerado, conservar a extensão enviada e rejeitar a extensão. A reavaliação alterou 33 gerações, todas de `reprovado` para `aprovado` nesses dois casos.

## Relato

Os resultados registrados permanecem em `dados/coleta-principal/analise.json`, e os corrigidos em `analise-emenda-02.json`. O artigo apresenta os dois. As conclusões sobre a T03 usam a versão corrigida, por haver falso positivo demonstrado. Como a correção é posterior aos dados, ela tem caráter de análise não prevista no plano, ainda que usem o mesmo código estatístico. Os demais verificadores não receberam correção semelhante nesta revisão, e a revisão manual cobriu oito gerações por tarefa.
