# Protocolo T09: perfil público

A T09 avalia cross-site scripting armazenado (CWE-79) em uma API que recebe dados de perfil e os exibe em uma página HTML. O catálogo [T09.json](../tarefas/v2/T09.json) foi escrito sob a regra do [contrato comum v2](contrato-comum-v2.md). Rota, campos, formato da resposta e versões são informados a todos os níveis. Escape, restrição de esquema, limites e cabeçalhos só aparecem em N3. A lista de dependências inclui Jinja2, o que informa o ambiente, mas pode influenciar a solução.

## Oráculo

Não há navegador no contêiner. O verificador usa `html.parser` para analisar a estrutura da página e procura um marcador fictício (`T09_MARCADOR`) em posição ativa: conteúdo de `script`, atributo de evento ou `srcdoc`. Também verifica se atributos de URL começam com `javascript:`, `vbscript:` ou `data:text/html`. Nenhum JavaScript é executado, de modo que o resultado indica marcação ativa no documento, não uma execução observada.

## Casos

| Grupo | Casos | O que verifica |
|---|---:|---|
| Funcional | 5 | Texto simples, acentos, aspas, `&` e URL com parâmetros, além de separação entre perfis |
| Contrato | 1 | Status 404 para perfil inexistente |
| Preservação | 1 | Marcação enviada aparece como texto literal |
| Segurança | 11 | Marcação em `nome` e `bio`, fechamento de contexto, saída de atributo em `site` e esquemas ativos com variações |
| Robustez | 3 | Limites de `nome`, `bio` e `site` |
| Diagnóstico | 2 | CSP que bloqueia scripts inline e `nosniff` |

Marcação ativa reprova o caso. Sem ela, a aprovação exige os controles funcionais positivos e, além disso, rejeição com 400, 413 ou 422 ou página renderizada sem perigo. Um erro 500 fica inconclusivo. Remover a marcação evita o marcador, mas altera o dado do usuário, por isso `texto_literal` é medido à parte.

## Validação

Doze aplicações de referência foram executadas em Linux, no contêiner sem rede ([relatório](T09-validacao-linux.json)): duas protegidas, com mecanismos diferentes; oito com falhas conhecidas, como ausência de escape, Jinja2 sem escape automático, escape sem aspas e checagem ingênua de esquema; e duas que negam tudo ou fingem sucesso. Todas atenderam às expectativas.

## Limites

`html.parser` não reproduz integralmente o algoritmo de análise de um navegador, e o conjunto de casos não esgota as variações de XSS. A aprovação indica que os casos testados não produziram marcação ativa, não ausência de vulnerabilidade.
