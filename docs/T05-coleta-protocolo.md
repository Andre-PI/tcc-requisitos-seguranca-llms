# Coleta exploratória T05 — decisões anteriores às chamadas

Esta coleta terá oito gerações: dois modelos datados, quatro níveis e uma repetição por combinação. É separada do piloto e das 800 gerações planejadas. Seu objetivo é validar o fluxo da tarefa, sem realizar comparação inferencial entre níveis.

## Registro e execução

O script `t05_coleta.py` grava o plano com a ordem sorteada pela semente 2026110305, prompts completos, identificador da imagem validada, hashes das fontes e parâmetros: temperatura 0,7, `max_completion_tokens=1500` e `store=false`. Os modelos são `gpt-4.1-mini-2025-04-14` e `gpt-5.4-mini-2026-03-17`. O plano deve preceder a primeira requisição.

```powershell
python t05_coleta.py
python t05_coleta.py --executar
```

Respostas completas, tentativas, identificadores de requisição e consumo de tokens serão preservados. O cliente da T04 será reutilizado sem alteração. Há até duas tentativas por erro transitório; uma falha de transporte pode ocorrer após processamento no servidor e será declarada nos registros. Não haverá nova geração por erro funcional, código inválido ou truncamento. Uma requisição interrompida de resultado desconhecido bloqueia repetição automática.

O executor já validado importará as amostras somente no contêiner sem rede. Cada cenário recebe uma aplicação e colaboradores novos. Não haverá correção do código coletado nem complementação de dependências fora do contrato. O envio de e-mail é fictício, por colaborador local.

## Leitura dos resultados

As capacidades funcionais são os dois ciclos de recuperação previstos no protocolo da tarefa. Oito casos de segurança, um contrato temporal e um diagnóstico de tokens são registrados à parte. Falha de importação ou execução sem controles funcionais não equivale a proteção aprovada. Nenhuma contagem de casos será tratada como amostras independentes.

Depois da execução, a inspeção do código registrará, por amostra: mecanismo e tamanho solicitado na geração dos tokens; presença de tokens em claro no estado de recuperação; emprego de resumo criptográfico; vínculo com a conta; consumo e expiração. A inspeção terá indicação de arquivo e linha e será identificada como revisão assistida por IA, pendente de revisão humana independente. Não substituirá o resultado comportamental.

A chamada a uma fonte criptográfica será descrita como evidência do mecanismo utilizado, sem alegar comprovação empírica de entropia. O diagnóstico de oito emissões apenas procura repetição e sequência decimal simples. Comprimento, diversidade ou passagem nessa verificação não serão convertidos em aprovação criptográfica. Quando o código estiver incompleto ou um requisito não puder ser determinado, a conclusão será inconclusiva.
