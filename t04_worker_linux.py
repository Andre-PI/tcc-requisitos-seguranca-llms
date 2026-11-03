"""Executa uma referência ou uma amostra no contêiner, nunca no host."""
import argparse
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path
import socket
import sys
from t04_verificador import preparar_arquivos, avaliar


def probe():
    tests={'usuario_sem_privilegios':os.getuid()!=0}
    try:
        Path('/var/tmp/tcc-probe-escrita').write_text('teste')
        tests['raiz_somente_leitura']=False
    except OSError:
        tests['raiz_somente_leitura']=True
    try:
        with socket.create_connection(('1.1.1.1',443),timeout=2):
            tests['rede_bloqueada']=False
    except OSError:
        tests['rede_bloqueada']=True
    tests['sem_chave_api']='OPENAI_API_KEY' not in os.environ
    fixture=preparar_arquivos('/tmp/fixtures')
    tests['link_simbolico_disponivel']=fixture['link_disponivel']
    return {'confinamento':tests,'python':sys.version,
            'dependencias':{p:version(p) for p in ['fastapi','starlette','pydantic','httpx','anyio','typing_extensions']}}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--probe',action='store_true')
    p.add_argument('--referencia')
    p.add_argument('--amostra',type=Path)
    args=p.parse_args()
    if args.probe:
        result=probe()
    else:
        fixture=preparar_arquivos('/tmp/fixtures')
        os.environ['TCC_ARQUIVOS_DIR']=str(fixture['base'])
        if args.referencia:
            from t04_referencias import criar_app
            app=criar_app(fixture['base'],args.referencia)
        elif args.amostra:
            spec=importlib.util.spec_from_file_location('amostra_t04',args.amostra)
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            app=module.app
        else:
            p.error('Informe referencia, amostra ou probe')
        result=avaliar(app,fixture)
        result['link_disponivel']=fixture['link_disponivel']
    print('TCC_RESULTADO_JSON:'+json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print('TCC_RESULTADO_JSON:'+json.dumps({'estado':'inconclusivo','erro':type(exc).__name__+': '+str(exc),'testes':[]},ensure_ascii=False))
        raise SystemExit(1)
