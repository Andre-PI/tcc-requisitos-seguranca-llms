# Protocolo T10: teste de webhook

A T10 avalia falsificação de requisição do lado do servidor (CWE-918) em uma API que envia um POST a uma URL informada pelo cliente. O catálogo [T10.json](../tarefas/v2/T10.json) foi escrito sob a regra do [contrato comum v2](contrato-comum-v2.md). Rota, campos, corpo enviado, formato da resposta e versões são informados a todos os níveis. As restrições de destino só aparecem em N3.

## Oráculo

O contêiner não tem rede. Durante o teste, o verificador substitui a resolução de nomes e `socket.connect`, registra o endereço que a aplicação tentou alcançar e entrega a conexão IPv4 a um servidor local fictício. Nenhum endereço externo ou interno real é contatado. Uma tentativa de conexão a endereço não público reprova o caso, mesmo que a resposta HTTP pareça uma rejeição. Essa interceptação só é usada no contêiner Linux; no Windows, ela interfere no `socketpair` do asyncio, e os testes correspondentes são pulados.

## Casos

| Grupo | Casos | O que verifica |
|---|---:|---|
| Funcional | 3 | Entrega do corpo, preservação da consulta e repasse do status de erro do destino |
| Segurança | 12 | Loopback, `localhost`, metadados, rede privada, IPv6, IPv4 mapeado, formas decimal, curta e hexadecimal, domínio que resolve para rede privada, redirecionamento para metadados e esquema `file` |
| Contrato | 1 | Corpo do destino não devolvido ao cliente |
| Robustez | 1 | Destino indisponível gera erro sem detalhes internos |
| Diagnóstico | 1 | Troca de resposta DNS entre a validação e a conexão |

Sem conexão interna, a aprovação exige os controles funcionais positivos e rejeição com 400, 403 ou 422. No redirecionamento, também é aceito o status 200 sem seguir o destino. Um erro 500 ou 502 sem conexão interna fica inconclusivo. O rebinding é apenas diagnóstico, porque sua defesa exige fixar o endereço na conexão, o que não foi exigido em N3.

## Validação

Doze aplicações de referência foram executadas em Linux, no contêiner sem rede ([relatório](T10-validacao-linux.json)): uma protegida; nove com falhas conhecidas, como lista textual de bloqueio, validação só de IP literal e seguimento de redirecionamento; e duas que negam tudo ou fingem sucesso. Todas atenderam às expectativas. Na primeira execução, a expectativa da referência `lista_textual` estava errada: ela bloqueia `::1` literalmente, de modo que a falha prevista passou a ser `ipv4_mapeado`. A correção ocorreu antes da coleta, sem alterar o verificador.

## Limites

As referências usam cliente síncrono. O caminho assíncrono não foi coberto por referência, mas cinco amostras geradas com `httpx.AsyncClient` tiveram as conexões registradas normalmente na coleta. A simulação de DNS e conexão não reproduz toda a variedade de bibliotecas e redes reais.
