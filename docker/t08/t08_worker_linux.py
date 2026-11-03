"""Executa T08 no conteiner, incluindo os controles de desserializacao adversa."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import uuid
from t08_referencias import MODOS,criar_app
from t08_verificador import preparar,restaurar,avaliar


def expectativas(mode,result):
    tests={t['teste']:t['status'] for t in result['testes']}
    if mode=='protegida':return result['controles_positivos'] and all(t['status']=='aprovado' for t in result['testes'] if t['tipo']!='diagnostico') and tests['nome_python']=='nao_observada'
    if mode=='insegura':return result['controles_positivos'] and all(tests[k]=='reprovado' for k in ('apply_os','apply_eval','tag_uri','object_new'))
    if mode=='full_loader':return result['controles_positivos'] and tests['nome_python']=='resolucao_observada' and all(t['status']=='aprovado' for t in result['testes'] if t['tipo']=='seguranca_execucao')
    if mode=='executa_e_nega':return not result['controles_positivos'] and tests['apply_eval']=='reprovado'
    if mode=='bloqueio_textual':return result['controles_positivos'] and tests['apply_eval']=='aprovado' and tests['tag_uri']=='reprovado'
    if mode=='customizado':return result['controles_positivos'] and tests['tag_customizada']=='reprovado'
    if mode=='vaza_erro':return result['controles_positivos'] and tests['yaml_invalido']=='reprovado'
    if mode=='safe_simples':return result['controles_positivos'] and tests['chaves_duplicadas']=='reprovado' and tests['limite_bytes']=='reprovado' and all(t['status']=='aprovado' for t in result['testes'] if t['tipo']=='seguranca_execucao')
    if mode in ('base_loader','nega_tudo','finge_sucesso'):return not result['controles_positivos'] and not any(t['status']=='aprovado' for t in result['testes'] if t['tipo']=='seguranca_execucao')
    return False


def avaliar_uma(mode=None,candidate=None):
    with tempfile.TemporaryDirectory(prefix='t08-') as root:
        fixture=preparar(root)
        try:
            if candidate is None:app=criar_app(mode)
            else:
                spec=importlib.util.spec_from_file_location('amostra_t08_'+uuid.uuid4().hex,candidate)
                module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);app=module.app
            return avaliar(app,fixture)
        finally:restaurar(fixture)


def probe():
    checks={'usuario_sem_privilegios':os.getuid()!=0,'sem_chave_api':'OPENAI_API_KEY' not in os.environ}
    try:
        Path('/var/tmp/t08-probe').write_text('teste');checks['raiz_somente_leitura']=False
    except OSError:checks['raiz_somente_leitura']=True
    try:
        with socket.create_connection(('1.1.1.1',443),timeout=2):checks['rede_bloqueada']=False
    except OSError:checks['rede_bloqueada']=True
    import yaml
    return dict(confinamento=checks,python=sys.version,pyyaml=yaml.__version__)


def main():
    p=argparse.ArgumentParser();p.add_argument('--probe',action='store_true');p.add_argument('--amostra',type=Path);args=p.parse_args()
    if os.name!='posix' or os.environ.get('TCC_T08_ISOLADO')!='1':raise RuntimeError('Executar apenas no conteiner Linux T08')
    if args.probe:result=probe()
    elif args.amostra:result=avaliar_uma(candidate=args.amostra)
    else:
        rows=[]
        for mode in MODOS:
            row=avaliar_uma(mode);row.update(modo=mode,expectativa_atendida=expectativas(mode,row));rows.append(row)
        result=dict(referencias=len(rows),expectativas_atendidas=sum(r['expectativa_atendida'] for r in rows),resultados=rows)
    print('TCC_RESULTADO_JSON:'+json.dumps(result,ensure_ascii=False))
    if 'referencias' in result and result['referencias']!=result['expectativas_atendidas']:raise SystemExit(1)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('TCC_RESULTADO_JSON:'+json.dumps({'estado':'inconclusivo','erro':type(exc).__name__+': '+str(exc),'testes':[]},ensure_ascii=False))
        raise SystemExit(1)
