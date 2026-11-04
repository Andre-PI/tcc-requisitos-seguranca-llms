# Emenda 01: gerações sem resposta por queda de rede

Desvio do [plano da coleta principal](plano-coleta-principal.md), registrado em 4 de novembro de 2026, depois de encerradas as demais gerações e antes de qualquer análise dos resultados.

## O que ocorreu

Durante a coleta, a internet caiu entre cerca de 10h12 e 10h26 (horário de Brasília). O plano previa até duas tentativas em erro de transporte, e o executor registrou como concluídas as gerações que falharam nas duas, em vez de interromper a coleta. Assim, 99 gerações consecutivas, de `cp-0435` a `cp-0533`, ficaram sem resposta de qualquer provedor e foram classificadas como inconclusivas.

## Tratamento

Essas gerações não contêm resultado de modelo. Por isso:

- os registros originais foram preservados em `dados/coleta-principal/falhas-de-rede/`, e a lista está em `dados/coleta-principal/emenda-01-rede.json`;
- as 99 gerações são refeitas com os mesmos prompts e parâmetros, depois das demais e, portanto, fora da ordem sorteada;
- `recuperar_rede.py` interrompe a coleta se a rede falhar de novo, sem registrar geração;
- nenhuma geração com resposta do provedor é refeita, inclusive as com código inválido, falha funcional ou resposta interrompida.

Antes desta emenda, foram consultados apenas contagens de progresso e os desfechos exibidos no log, sem comparação estatística. A seleção usa um critério objetivo: nenhuma tentativa recebeu resposta HTTP do provedor.

## Efeitos

As gerações refeitas foram coletadas algumas horas depois das demais, em ordem própria. Uma mudança no serviço dos provedores nesse intervalo afetaria apenas esse grupo. A amostra foi sorteada em ordem aleatória, mas as 99 gerações formam um bloco contínuo, cuja distribuição por tarefa, modelo e nível consta da lista. O executor original permanece inalterado, conforme o plano publicado.
