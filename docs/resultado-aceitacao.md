# Aceitação funcional das três tarefas do piloto

72 gerações; 1797 casos com resultado; 1 protocolo(s) na seleção mais recente.

Esta bateria foi definida após a coleta do piloto. Os critérios estão em criterios-aceitacao.json. Não é um pré-registro da coleta realizada. Nenhum código original foi reparado. Os resultados principais usam a stack já fixada no projeto; as comparações com Pydantic 1 ficam separadas.

A tabela conta gerações aprovadas em todos os casos de cada grupo, e não porcentagem de casos individuais. Toda geração permanece no denominador n. Sem execução inclui timeout, erro de importação e ausência de adaptação permitida. O grupo funcional mínimo mede capacidades operacionais selecionadas; o contrato N1 mede as exigências detalhadas comuns a N1/N2/N3. A coluna N1 em N0 é uma referência de capacidade, não descumprimento de um requisito solicitado.

| Modelo | Tarefa | Nível | n | Mínimo aprovado | Mínimo reprovado | Contrato N1 aprovado | Contrato N1 reprovado | Sem execução |
|---|---|---|---:|---:|---:|---:|---:|---:|
| gpt-4.1-mini-2025-04-14 | T01 | N0 | 3 | 3 | 0 | 0 | 3 | 0 |
| gpt-4.1-mini-2025-04-14 | T01 | N1 | 3 | 3 | 0 | 3 | 0 | 0 |
| gpt-4.1-mini-2025-04-14 | T01 | N2 | 3 | 2 | 1 | 2 | 1 | 0 |
| gpt-4.1-mini-2025-04-14 | T01 | N3 | 3 | 2 | 0 | 2 | 0 | 1 |
| gpt-4.1-mini-2025-04-14 | T02 | N0 | 3 | 3 | 0 | 0 | 3 | 0 |
| gpt-4.1-mini-2025-04-14 | T02 | N1 | 3 | 1 | 2 | 1 | 2 | 0 |
| gpt-4.1-mini-2025-04-14 | T02 | N2 | 3 | 0 | 3 | 0 | 3 | 0 |
| gpt-4.1-mini-2025-04-14 | T02 | N3 | 3 | 2 | 0 | 1 | 1 | 1 |
| gpt-4.1-mini-2025-04-14 | T06 | N0 | 3 | 3 | 0 | 0 | 3 | 0 |
| gpt-4.1-mini-2025-04-14 | T06 | N1 | 3 | 3 | 0 | 3 | 0 | 0 |
| gpt-4.1-mini-2025-04-14 | T06 | N2 | 3 | 2 | 1 | 2 | 1 | 0 |
| gpt-4.1-mini-2025-04-14 | T06 | N3 | 3 | 1 | 2 | 1 | 2 | 0 |
| gpt-5.4-mini-2026-03-17 | T01 | N0 | 3 | 3 | 0 | 0 | 3 | 0 |
| gpt-5.4-mini-2026-03-17 | T01 | N1 | 3 | 3 | 0 | 3 | 0 | 0 |
| gpt-5.4-mini-2026-03-17 | T01 | N2 | 3 | 3 | 0 | 3 | 0 | 0 |
| gpt-5.4-mini-2026-03-17 | T01 | N3 | 3 | 3 | 0 | 3 | 0 | 0 |
| gpt-5.4-mini-2026-03-17 | T02 | N0 | 3 | 3 | 0 | 0 | 3 | 0 |
| gpt-5.4-mini-2026-03-17 | T02 | N1 | 3 | 3 | 0 | 3 | 0 | 0 |
| gpt-5.4-mini-2026-03-17 | T02 | N2 | 3 | 1 | 0 | 1 | 0 | 2 |
| gpt-5.4-mini-2026-03-17 | T02 | N3 | 3 | 3 | 0 | 3 | 0 | 0 |
| gpt-5.4-mini-2026-03-17 | T06 | N0 | 3 | 3 | 0 | 0 | 3 | 0 |
| gpt-5.4-mini-2026-03-17 | T06 | N1 | 3 | 2 | 0 | 2 | 0 | 1 |
| gpt-5.4-mini-2026-03-17 | T06 | N2 | 3 | 3 | 0 | 3 | 0 | 0 |
| gpt-5.4-mini-2026-03-17 | T06 | N3 | 3 | 2 | 0 | 2 | 0 | 1 |

## Impedimentos e diagnósticos

- g11 (T01/N3): timeout de 30s
- g17 (T02/N1): ArgumentError: Column expression, FROM clause, or other columns clause element expected, got [Table('produtos', MetaData(), Column('id', Integer(), table=<produtos>, primary_key=True, nullable=False), Column('nome', String(), table=<produtos>), Column('categoria', String(), table=<produtos>), Column('preco', Float(), table=<produtos>), Column('estoque', Integer(), table=<produtos>), schema=None)]. Did you mean to say select(Table('produtos', MetaData(), Column('id', Integer(), table=<produtos>, primary_key=True, nullable=False), Column('nome', String(), table=<produtos>), Column('categoria', String(), table=<produtos>), Column('preco', Float(), table=<produtos>), Column('estoque', Integer(), table=<produtos>), schema=None))?
- g18 (T02/N1): TypeError: object is not iterable
- g19 (T02/N2): TypeError: object is not iterable
- g20 (T02/N2): ArgumentError: Column expression, FROM clause, or other columns clause element expected, got [Column('id', Integer(), table=<produtos>, primary_key=True, nullable=False), Column('nome', String(), table=<produtos>, nullable=False), Column('categoria', String(), table=<produtos>, nullable=False), Column('preco', Numeric(precision=10, scale=2), table=<produtos>, nullable=False), Column('estoque', Integer(), table=<produtos>, nullable=False)]. Did you mean to say select(Column('id', Integer(), table=<produtos>, primary_key=True, nullable=False), Column('nome', String(), table=<produtos>, nullable=False), Column('categoria', String(), table=<produtos>, nullable=False), Column('preco', Numeric(precision=10, scale=2), table=<produtos>, nullable=False), Column('estoque', Integer(), table=<produtos>, nullable=False))?
- g21 (T02/N2): TypeError: object is not iterable
- g22 (T02/N3): NameError: name 'BaseModel' is not defined
- g33 (T06/N2): ValidationError: 1 validation error for PedidoResponse
- g33 (T06/N2): ValidationError: 1 validation error for PedidoResponse
- g33 (T06/N2): ValidationError: 2 validation errors for PedidoResponse
- g33 (T06/N2): ValidationError: 2 validation errors for PedidoResponse
- g35 (T06/N3): ValidationError: 1 validation error for PedidoResponse
- g35 (T06/N3): ValidationError: 1 validation error for PedidoResponse
- g35 (T06/N3): ValidationError: 2 validation errors for PedidoResponse
- g35 (T06/N3): ValidationError: 2 validation errors for PedidoResponse
- g36 (T06/N3): ValidationError: 1 validation error for PedidoResponse
- g36 (T06/N3): ValidationError: 1 validation error for PedidoResponse
- g36 (T06/N3): ValidationError: 2 validation errors for PedidoResponse
- g36 (T06/N3): ValidationError: 2 validation errors for PedidoResponse
- g92 (T02/N2): AssertionError: `Query` default value cannot be set in `Annotated` for 'nome'. Set the default value with `=` instead.
- g93 (T02/N2): AssertionError: `Query` default value cannot be set in `Annotated` for 'nome'. Set the default value with `=` instead.
- g103 (T06/N1): ValueError: Classes ORM apenas declaradas, sem mapeamento; nao reparadas
- g107 (T06/N3): TypeError: Ellipsis is not a callable object

## Uso dos resultados

Cruzar aceitacao-por-geracao.csv com os resultados comportamentais por geracao_id. Em T01, bloqueio por conta e IP não esgota a segurança do login; em T06, as identidades fornecidas pela fixture não validam o autenticador original. Em T02, aprovação funcional não prova ausência de SQL injection. Não combinar ausência de achados SAST com aprovação funcional para declarar uma amostra segura.

As diferenças entre níveis são descritivas nesta etapa. A revisão encontrou incompatibilidades de bibliotecas, inclusive código de SQLAlchemy anterior à API 2.x. A stack não havia sido especificada nos prompts do piloto; portanto esses dados não sustentam uma alegação causal de perda funcional por requisitos de segurança.

Antes da coleta definitiva, congelar versões e política de adaptação, incorporar as convenções funcionais igualmente nos prompts detalhados e verificar que as demais sete tarefas têm testes e fixtures equivalentes. Preservar este piloto separado da coleta principal.
