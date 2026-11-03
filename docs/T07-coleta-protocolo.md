# Coleta exploratória T07 — decisões anteriores às chamadas

Serão oito gerações, uma para cada combinação de quatro níveis e dois modelos datados: gpt-4.1-mini-2025-04-14 e gpt-5.4-mini-2026-03-17. Esta coleta valida o procedimento da tarefa e permanece separada das 72 gerações do piloto e das 800 previstas para o experimento principal.

O plano registra os prompts completos, a ordem sorteada com semente 2026110307, os hashes das fontes, o identificador da imagem Linux e os parâmetros: temperatura 0,7, max_completion_tokens=1500 e store=false. O registro deve preceder a primeira requisição.

```powershell
python t07_coleta.py
python t07_coleta.py --executar
```

O primeiro comando registra o plano sem chamar a API. O segundo realiza chamadas pagas e avalia os códigos no contêiner sem rede. O cliente e a persistência da T04 são reutilizados sem alteração. Respostas brutas, tentativas, identificadores e uso de tokens são preservados. Há até duas tentativas em erros transitórios; falhas de transporte podem ocorrer depois do processamento no servidor e serão declaradas. Requisições interrompidas de resultado desconhecido bloqueiam repetição automática.

Nenhuma amostra será regenerada por reprovação funcional, código inválido ou resposta truncada. Não haverá correção do código coletado nem instalação de dependências fora do contrato. A avaliação usa o utilitário e os dados fictícios já validados pelas dez aplicações de referência.

Os cinco controles funcionais, os sete casos de injeção de comandos, a injeção de argumentos, o formato inválido e a falha controlada do utilitário permanecem em grupos distintos. A ausência de marcador só é aprovada nos termos do protocolo da tarefa; uma falha geral de execução não demonstra proteção.

Após a execução, a revisão do código identificará o mecanismo de criação do processo, o uso explícito ou padrão de shell, a origem do executável, a estrutura dos argumentos, o delimitador de opções e o tratamento do código de saída. As observações terão indicação de arquivo, linha e hash. Essa revisão será identificada como assistida por IA e pendente de conferência humana independente. Ela não substituirá os resultados comportamentais nem atribuirá ausência geral de CWE-78 a uma aplicação que passe nos vetores.
