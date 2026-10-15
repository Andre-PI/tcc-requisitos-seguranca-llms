# Especificação de requisitos, segurança e correção funcional

Material do estudo piloto do TCC de Engenharia de Software do iCEV, de Andre Lucas Francino Castelo Branco, orientado por Mauro José Araújo de Melo.

**Estado do estudo:** piloto com 72 gerações realizado. O experimento principal de 800 gerações permanece planejado. Esta versão é um pacote para orientação e auditoria do piloto.

## Roteiro para o orientador

1. Leia [a metodologia](orientacao/Metodologia-v03.pdf); há também um [Word editável](orientacao/Metodologia-v03.docx).
2. Consulte [o exemplo de acesso a pedidos](exemplos/acesso-a-pedidos.md), que relaciona prompt, código e resposta do teste.
3. Confira [a aceitação funcional](docs/resultado-aceitacao.md) e [os testes comportamentais](docs/resultado-comportamental.md).
4. Examine os CSV em `dados/` e `docs/`. O arquivo `resultados.db` conserva os registros detalhados, inclusive versões anteriores das verificações.
5. Execute `python conferir_pacote.py` para conferir integridade, contagens e correspondência dos códigos, sem chamar a API nem executar as aplicações geradas.

O referencial foi entregue anteriormente e não está duplicado nesta entrega. A metodologia é uma versão parcial para avaliação do desenho e dos critérios.

## Conteúdo

- `codigos/`: 72 códigos originais, sem reparo.
- `dados/geracoes.jsonl`: prompts, respostas e código em formato aberto; `geracoes.csv`: índice.
- `dados/achados.csv` e `relatorios-sast/`: achados e relatórios originais dos analisadores.
- `dados/*-mais-recentes.json`: verificações selecionadas pela maior identificação por geração, conforme os resumos do piloto.
- `execucoes/`: código, resultados, saídas e erros das execuções selecionadas; os caminhos históricos foram conservados. Bancos temporários dos testes foram omitidos.
- `docs/`: critérios, protocolos, resultados e análise dos sete casos.
- Scripts Python e `tests/`: coleta, análise, verificadores e controles do próprio instrumento.
- `manifesto-pacote.json`: SHA-256 dos arquivos desta cópia. Os hashes detectam alterações posteriores; não comprovam, por si só, autenticidade da coleta.

Os hashes do manifesto cobrem os bytes dos arquivos. A comparação entre as exportações Python e o banco normaliza apenas finais de linha CRLF/LF, devido à gravação dos arquivos no Windows; o conteúdo do código é preservado.

## Resultados que podem ser conferidos

72 gerações, 36 por modelo; 72 análises estáticas; quatro alertas Bandit em duas gerações. Na aceitação mínima: 57 aprovadas, nove reprovadas e seis sem execução conclusiva. A bateria registrou 1.797 resultados de casos; a unidade de análise continua sendo a geração. Há 48 gerações T01/T06 na avaliação comportamental.

Os critérios ampliados de aceitação foram definidos depois da coleta. Identidades e infraestrutura foram fornecidas conforme a política documentada. Aprovação nos testes não comprova segurança completa; falhas de compatibilidade não demonstram custo funcional causado por requisitos de segurança.

## Reprodução

A conferência do pacote usa somente a biblioteca padrão do Python 3.11 ou posterior:

```powershell
python conferir_pacote.py
```

Para reproduzir os testes, trabalhe em uma cópia deste repositório, pois os scripts gravam novos registros no banco. O ambiente original era Python 3.14.2, com versões em `requirements-lock.txt`. No PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe validar_aceitacao.py --ids 25 34
.\.venv\Scripts\python.exe verificar.py --ids 25 34
```

Os dois últimos comandos executam código gerado. Leia antes a política e os limites de isolamento em `docs/protocolo-comportamental.md`. Os registros incluem diretórios e versões históricas da máquina de coleta; outra máquina terá caminhos diferentes. Repetir geração em API não garante os mesmos programas. As regras remotas `p/python` do Semgrep podem mudar.

`piloto.py` realiza chamadas pagas à API quando invocado para geração. Nenhuma chave é necessária para consultar os dados ou executar a conferência do pacote. Não execute uma nova coleta para tentar reproduzir os códigos arquivados.

## Compartilhamento

Repositório público para consulta e conferência das evidências do piloto: https://github.com/Andre-PI/tcc-requisitos-seguranca-llms. O acesso não exige convite de colaborador. Não foi atribuída uma licença de redistribuição; a disponibilidade pública não implica autorização irrestrita de reutilização.
