# Validação do instrumento T04

Esta execução usa aplicações de referência locais. Não contém gerações de LLM e não integra os resultados do piloto.

| Referência | Download legítimo | Exposições | Abertura externa sem exposição | Inconclusivos | Não executados | Expectativa atendida |
|---|---|---:|---:|---:|---:|---|
| protegida | sim | 0 | 0 | 0 | 1 | sim |
| vulneravel | sim | 6 | 0 | 0 | 1 | sim |
| nega_tudo | não | 0 | 0 | 8 | 1 | sim |
| le_e_nega | sim | 0 | 6 | 0 | 1 | sim |
| prefixo_ingenuo | sim | 1 | 0 | 0 | 1 | sim |
| bytes_errados | não | 0 | 0 | 8 | 1 | sim |
| decodifica_novamente | sim | 7 | 0 | 0 | 1 | sim |

O número de casos não executados informa, entre outras condições, indisponibilidade de links simbólicos. Não é aprovação dessa propriedade.

Protocolo SHA-256: `2ac2005d606f951ba625e6a06e14057dccd4d543c4c4f89d4152f6f34f318825`.

Dados completos e evidências por requisição: [T04-validacao.json](T04-validacao.json).
