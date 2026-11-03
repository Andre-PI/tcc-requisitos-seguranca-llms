"""Diagnostico separado: dependencias opcionais e dominio dos colaboradores."""
import json
import sys
from pydantic import EmailStr,TypeAdapter,ValidationError
import t05_infra
import t05_verificador
import t05_worker_linux


if __name__=='__main__':
    if '--verificar-email' in sys.argv:
        result={}
        for value in ['alice@example.test','alice@example.com']:
            try:TypeAdapter(EmailStr).validate_python(value);result[value]='aceito'
            except ValidationError:result[value]='rejeitado'
        print('TCC_RESULTADO_JSON:'+json.dumps(result))
    else:
        if '--dominio-example' in sys.argv:
            sys.argv.remove('--dominio-example')
            for module in [t05_infra,t05_verificador]:
                module.A='alice@example.com';module.B='bruno@example.com';module.UNKNOWN='ausente@example.com'
            t05_verificador.solicitar.__defaults__=(t05_infra.A,)
        try:t05_worker_linux.main()
        except Exception as exc:
            print('TCC_RESULTADO_JSON:'+json.dumps({'estado':'inconclusivo','erro':type(exc).__name__+': '+str(exc),'testes':[]}))
            raise SystemExit(1)
