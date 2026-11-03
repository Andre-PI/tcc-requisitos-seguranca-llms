"""Valida T04 somente com referências locais; não chama API nem importa amostras LLM."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def dump(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))


def worker(modo, folder):
    from t04_verificador import preparar_arquivos, avaliar
    from t04_referencias import criar_app
    fixture=preparar_arquivos(folder)
    result=avaliar(criar_app(fixture['base'],modo),fixture)
    result.update(modo=modo,link_disponivel=fixture['link_disponivel'])
    return result


def expectations(mode, result):
    cases={t['teste']:t for t in result['testes']}
    security=[t for t in result['testes'] if t['tipo']=='seguranca']
    if mode=='protegida':
        return result['controles_positivos'] and all(t['status'] in ('aprovado','nao_executado') for t in result['testes'])
    if mode in ('nega_tudo','bytes_errados'):
        return not result['controles_positivos'] and all(t['status'] in ('inconclusivo','nao_executado') for t in security)
    if mode=='le_e_nega':
        case=cases['subida_simples']
        return result['controles_positivos'] and case['status']=='acesso_externo_observado' and case['evidencia']['status_http']==404
    target='diretorio_com_prefixo' if mode=='prefixo_ingenuo' else 'dupla_codificacao' if mode=='decodifica_novamente' else 'subida_simples'
    return result['controles_positivos'] and cases[target]['status']=='exposicao'


def main():
    from t04_referencias import MODOS
    from t04_verificador import montar_prompt
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prompts',action='store_true',help='exporta os quatro prompts, sem executar aplicações')
    p.add_argument('--worker',choices=MODOS,help=argparse.SUPPRESS)
    p.add_argument('--pasta',type=Path,help=argparse.SUPPRESS)
    args=p.parse_args()
    if args.worker:
        if args.pasta is None:p.error('worker exige pasta de fixtures')
        print(json.dumps(worker(args.worker,args.pasta),ensure_ascii=False))
        return
    prompts={n:montar_prompt(n) for n in ['N0','N1','N2','N3']}
    dump(ROOT/'docs'/'T04-prompts.json',{n:dict(prompt=text,caracteres=len(text),sha256=hashlib.sha256(text.encode()).hexdigest()) for n,text in prompts.items()})
    if args.prompts:
        print('Quatro prompts exportados em docs/T04-prompts.json; nenhuma chamada de API.')
        return
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    artifacts=ROOT/'tmp'/'t04'/stamp
    artifacts.mkdir(parents=True,exist_ok=True)
    environment={k:v for k,v in os.environ.items() if k.upper() in {'SYSTEMROOT','WINDIR','TEMP','TMP','PATH','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}}
    environment.update(PYTHONIOENCODING='utf-8',PYTHONUTF8='1')
    results=[]
    for mode in MODOS:
        folder=artifacts/mode;folder.mkdir()
        try:
            process=subprocess.run([sys.executable,str(ROOT/'validar_t04.py'),'--worker',mode,'--pasta',str(folder)],
                                   cwd=folder,env=environment,capture_output=True,text=True,encoding='utf-8',timeout=30)
            (folder/'stdout.json').write_text(process.stdout,encoding='utf-8')
            (folder/'stderr.txt').write_text(process.stderr,encoding='utf-8')
            if process.returncode:raise RuntimeError('Subprocesso terminou com erro; consultar artefatos')
            result=json.loads(process.stdout)
            result['expectativa_atendida']=bool(expectations(mode,result))
        except (subprocess.TimeoutExpired,RuntimeError,json.JSONDecodeError) as exc:
            result=dict(modo=mode,expectativa_atendida=False,erro=type(exc).__name__,testes=[])
        results.append(result)
    protocol=dict(versao='t04-validacao-1',python=sys.version,plataforma=platform.platform(),
                  dependencias={n:version(n) for n in ['fastapi','starlette','httpx','pydantic']},
                  arquivos={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['tarefas/T04.json','t04_verificador.py','t04_referencias.py','validar_t04.py']},
                  timeout_referencia=30,observacao='Referencias escritas localmente; nao sao geracoes de LLM; nao e sandbox.')
    report=dict(criado_em=datetime.now(timezone.utc).isoformat(),protocolo=protocol,
                protocolo_sha256=hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest(),
                expectativas_atendidas=sum(r['expectativa_atendida'] for r in results),
                referencias=len(results),resultados=results)
    dump(ROOT/'docs'/'T04-validacao.json',report)
    lines=['# Validação do instrumento T04','',
           'Esta execução usa aplicações de referência locais. Não contém gerações de LLM e não integra os resultados do piloto.',
           '', '| Referência | Download legítimo | Exposições | Abertura externa sem exposição | Inconclusivos | Não executados | Expectativa atendida |',
           '|---|---|---:|---:|---:|---:|---|']
    for r in results:
        counts=Counter(t['status'] for t in r['testes'] if t['tipo']=='seguranca')
        lines.append(f"| {r['modo']} | {'sim' if r.get('controles_positivos') else 'não'} | {counts['exposicao']} | {counts['acesso_externo_observado']} | {counts['inconclusivo']} | {counts['nao_executado']} | {'sim' if r['expectativa_atendida'] else 'não'} |")
    lines+=['','O número de casos não executados informa, entre outras condições, indisponibilidade de links simbólicos. Não é aprovação dessa propriedade.',
            '', 'Protocolo SHA-256: `'+report['protocolo_sha256']+'`.',
            '', 'Dados completos e evidências por requisição: [T04-validacao.json](T04-validacao.json).']
    (ROOT/'docs'/'T04-validacao.md').write_bytes(('\n'.join(lines)+'\n').encode('utf-8'))
    print(f"T04: {report['expectativas_atendidas']}/{report['referencias']} referências corresponderam ao resultado esperado.")
    if report['expectativas_atendidas']!=report['referencias']:raise SystemExit(1)


if __name__=='__main__':main()
