"""Executa controles T05 ou importa uma amostra apenas dentro do conteiner."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import uuid
from t05_referencias import MODOS,criar_app
from t05_verificador import avaliar


def expectativas(mode,result):
    tests={t['teste']:t['status'] for t in result['testes']}
    if mode=='protegida':return result['controles_positivos'] and all(t['status']=='aprovado' for t in result['testes'] if t['tipo']!='diagnostico') and tests['diagnostico_tokens']=='sem_fraqueza_observada'
    expected={'reutiliza':'token_reutilizado','nao_expira':'validade:900','ignora_token':'token_inexistente',
              'troca_conta':'vinculo_da_conta','vaza_token':'token_na_resposta','enumera':'resposta_uniforme',
              'muda_ao_solicitar':'sem_alteracao_na_solicitacao'}
    if mode in expected:return result['controles_positivos'] and tests[expected[mode]]=='reprovado'
    if mode=='token_sequencial':return result['controles_positivos'] and tests['diagnostico_tokens']=='fraqueza_observada'
    if mode in ('nega_tudo','finge_sucesso'):
        return not result['controles_positivos'] and all(t['status']!='aprovado' for t in result['testes'] if t['tipo']=='seguranca')
    return False


def probe():
    checks={'usuario_sem_privilegios':os.getuid()!=0,'sem_chave_api':'OPENAI_API_KEY' not in os.environ}
    try:
        Path('/var/tmp/t05-probe').write_text('teste');checks['raiz_somente_leitura']=False
    except OSError:checks['raiz_somente_leitura']=True
    try:
        with socket.create_connection(('1.1.1.1',443),timeout=2):checks['rede_bloqueada']=False
    except OSError:checks['rede_bloqueada']=True
    return dict(confinamento=checks,python=sys.version)


def main():
    p=argparse.ArgumentParser();p.add_argument('--probe',action='store_true');p.add_argument('--amostra',type=Path);args=p.parse_args()
    if args.probe:result=probe()
    elif args.amostra:
        def factory(infra):
            sys.modules['tcc_t05_infra']=infra
            spec=importlib.util.spec_from_file_location('amostra_t05_'+uuid.uuid4().hex,args.amostra)
            module=importlib.util.module_from_spec(spec)
            sys.modules[spec.name]=module
            spec.loader.exec_module(module)
            return module.app
        result=avaliar(factory)
    else:
        rows=[]
        for mode in MODOS:
            row=avaliar(lambda infra:criar_app(infra,mode));row.update(modo=mode,expectativa_atendida=expectativas(mode,row));rows.append(row)
        result=dict(referencias=len(rows),expectativas_atendidas=sum(r['expectativa_atendida'] for r in rows),resultados=rows)
    print('TCC_RESULTADO_JSON:'+json.dumps(result,ensure_ascii=False))
    if 'referencias' in result and result['referencias']!=result['expectativas_atendidas']:raise SystemExit(1)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('TCC_RESULTADO_JSON:'+json.dumps({'estado':'inconclusivo','erro':type(exc).__name__+': '+str(exc),'testes':[]},ensure_ascii=False))
        raise SystemExit(1)
