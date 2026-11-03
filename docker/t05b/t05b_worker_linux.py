"""T05b: mesmo verificador da T05, com enderecos ficticios aceitos pelo email-validator."""
import json
import sys
from pydantic import EmailStr, TypeAdapter
import t05_infra
import t05_verificador
import t05_worker_linux

for modulo in (t05_infra, t05_verificador):
    modulo.A = 'alice@example.com'
    modulo.B = 'bruno@example.com'
    modulo.UNKNOWN = 'ausente@example.com'
t05_verificador.solicitar.__defaults__ = (t05_infra.A,)


if __name__ == '__main__':
    try:
        TypeAdapter(EmailStr).validate_python(t05_infra.A)
        t05_worker_linux.main()
    except Exception as exc:
        print('TCC_RESULTADO_JSON:' + json.dumps({'estado': 'inconclusivo', 'erro': type(exc).__name__ + ': ' + str(exc), 'testes': []}, ensure_ascii=False))
        raise SystemExit(1)
