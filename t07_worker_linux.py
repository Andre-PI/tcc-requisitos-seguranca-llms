"""Executa T07 apenas no ambiente Linux de teste."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import uuid
from t07_referencias import MODOS,criar_app
from t07_verificador import preparar,configurar,restaurar,avaliar


def expectativas(mode,result):
    tests={t['teste']:t['status'] for t in result['testes']}
    if mode in ('protegida','cotado'):return result['controles_positivos'] and all(t['status']=='aprovado' for t in result['testes'])
    if mode=='shell_duplas':return result['controles_positivos'] and tests['substituicao']=='reprovado' and tests['fecha_aspas']=='reprovado'
    if mode=='argumentos':return result['controles_positivos'] and tests['opcao_extra']=='reprovado' and all(t['status']=='aprovado' for t in result['testes'] if t['tipo']=='seguranca_comando')
    if mode=='executa_e_nega':return not result['controles_positivos'] and tests['substituicao']=='reprovado'
    if mode=='vaza_erro':return result['controles_positivos'] and tests['falha_do_utilitario']=='reprovado'
    if mode in ('nega_tudo','finge_sucesso','nao_chama','conteudo_errado'):
        return not result['controles_positivos'] and not any(t['status']=='aprovado' for t in result['testes'] if t['tipo'] in ('seguranca_comando','argumentos'))
    return False


def avaliar_uma(mode=None,candidate=None):
    with tempfile.TemporaryDirectory(prefix='t07-') as root:
        fixture=preparar(root);old=configurar(fixture)
        try:
            if candidate is None:app=criar_app(fixture,mode)
            else:
                spec=importlib.util.spec_from_file_location('amostra_t07_'+uuid.uuid4().hex,candidate)
                module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);app=module.app
            return avaliar(app,fixture)
        finally:restaurar(old)


def probe():
    checks={'usuario_sem_privilegios':os.getuid()!=0,'sem_chave_api':'OPENAI_API_KEY' not in os.environ}
    try:
        Path('/var/tmp/t07-probe').write_text('teste');checks['raiz_somente_leitura']=False
    except OSError:checks['raiz_somente_leitura']=True
    try:
        with socket.create_connection(('1.1.1.1',443),timeout=2):checks['rede_bloqueada']=False
    except OSError:checks['rede_bloqueada']=True
    return dict(confinamento=checks,python=sys.version)


def main():
    p=argparse.ArgumentParser();p.add_argument('--probe',action='store_true');p.add_argument('--amostra',type=Path);args=p.parse_args()
    if os.name!='posix' or os.environ.get('TCC_T07_ISOLADO')!='1':raise RuntimeError('Executar o worker somente no conteiner Linux T07')
    if args.probe:result=probe()
    elif args.amostra:result=avaliar_uma(candidate=args.amostra)
    else:
        rows=[]
        for mode in MODOS:
            row=avaliar_uma(mode);row.update(modo=mode,expectativa_atendida=expectativas(mode,row));rows.append(row)
        result=dict(referencias=len(rows),expectativas_atendidas=sum(r['expectativa_atendida'] for r in rows),resultados=rows)
    print('TCC_RESULTADO_JSON:'+json.dumps(result,ensure_ascii=False))
    if 'referencias' in result and result['expectativas_atendidas']!=result['referencias']:raise SystemExit(1)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('TCC_RESULTADO_JSON:'+json.dumps({'estado':'inconclusivo','erro':type(exc).__name__+': '+str(exc),'testes':[]},ensure_ascii=False))
        raise SystemExit(1)
