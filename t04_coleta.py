"""Pequena coleta T04: plano prospectivo, oito amostras e execução só no Docker."""
import argparse
import ast
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import random
import re
import time
import urllib.error
import urllib.request
import uuid
from t04_verificador import montar_prompt
from t04_docker import image_id, run

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'dados'/'t04-exploratoria'
MODELS=['gpt-4.1-mini-2025-04-14','gpt-5.4-mini-2026-03-17']
SOURCES=['tarefas/T04.json','t04_verificador.py','t04_referencias.py','t04_worker_linux.py',
         't04_docker.py','t04_coleta.py','docker/t04/Dockerfile','docker/t04/requirements.txt']


def now():return datetime.now(timezone.utc).isoformat()


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    for retry in range(10):
        try:
            temp.replace(path)
            break
        except PermissionError:
            if retry==9:raise
            time.sleep(0.1*(retry+1))


def fingerprints():return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}


def plan():
    file=DATA/'plano.json'
    if file.exists():
        frozen=json.loads(file.read_text(encoding='utf-8'))
        expected=frozen['fontes_sha256']
        amendment=DATA/'emendas.json'
        if amendment.exists():
            for change in json.loads(amendment.read_text(encoding='utf-8')):
                assert change['fontes_anteriores']==expected
                expected=change['fontes_atuais']
        assert expected==fingerprints(),'Fontes mudaram sem registro de emenda; criar novo protocolo'
        assert frozen['imagem']==image_id(),'Imagem mudou depois do registro'
        return frozen
    validation=json.loads((ROOT/'docs'/'T04-validacao-linux.json').read_text(encoding='utf-8'))
    assert validation['expectativas_atendidas']==validation['referencias']==7
    assert validation['imagem']==image_id()
    assert all(validation['probe']['confinamento'].values())
    jobs=[{'modelo':m,'nivel':n,'repeticao':1} for m in MODELS for n in ['N0','N1','N2','N3']]
    random.Random(20261103).shuffle(jobs)
    for i,j in enumerate(jobs,1):j.update(id=f't04-{i:02d}',prompt=montar_prompt(j['nivel']))
    frozen=dict(versao='t04-exploratoria-1',registrado_em=now(),natureza='Exploratoria, oito chamadas planejadas; fora do piloto e das 800 geracoes principais',
                semente_ordem=20261103,jobs=jobs,imagem=image_id(),fontes_sha256=fingerprints(),
                parametros={'temperature':0.7,'max_completion_tokens':1500,'store':False},
                retentativas='Ate duas tentativas somente em erro HTTP transitorio ou de transporte; nenhuma regeneracao por falha funcional',
                criterios='docs/T04-protocolo.md; t04_verificador.py; todas as respostas e falhas preservadas')
    save(file,frozen)
    return frozen


def api_key():
    key=os.environ.get('OPENAI_API_KEY')
    if not key and os.name=='nt':
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as registry:
            key=winreg.QueryValueEx(registry,'OPENAI_API_KEY')[0]
    if not key:raise RuntimeError('OPENAI_API_KEY indisponivel; nao enviar chave no chat')
    return key


def extract(text):
    blocks=re.findall(r'```(?:python)?\s*\n(.*?)```',text,re.DOTALL)
    return '\n\n'.join(b.strip() for b in blocks) if blocks else text.strip()


def collect(job,frozen):
    folder=DATA/job['id'];folder.mkdir(parents=True,exist_ok=True)
    file=folder/'geracao.json'
    if file.exists():
        record=json.loads(file.read_text(encoding='utf-8'))
        if 'concluida_em' not in record:
            raise RuntimeError('Requisicao interrompida; nao repetir automaticamente uma chamada de resultado desconhecido')
        return record
    key=api_key()
    payload={'model':job['modelo'],'messages':[{'role':'user','content':job['prompt']}],**frozen['parametros']}
    record=dict(**job,iniciado_em=now(),payload=payload,tentativas=[],resposta=None,erro=None)
    for attempt in range(1,3):
        entry=dict(numero=attempt,iniciada_em=now())
        record['tentativas'].append(entry);save(file,record)
        try:
            req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload).encode(),
                                       headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(req,timeout=180) as response:
                entry.update(http=response.status,request_id=response.headers.get('x-request-id'))
                record['resposta']=json.load(response)
            break
        except urllib.error.HTTPError as exc:
            entry.update(http=exc.code,erro=exc.read().decode(errors='replace').replace(key,'[REDACTED]')[:2000])
            if exc.code not in (429,500,502,503,504):break
        except (urllib.error.URLError,TimeoutError,OSError) as exc:
            entry['erro']=type(exc).__name__
        finally:
            entry['terminada_em']=now();save(file,record)
        if attempt<2:time.sleep(2)
    if record['resposta'] is None:
        record['erro']='Nenhuma resposta de geracao; consultar tentativas'
    else:
        choice=record['resposta']['choices'][0]
        text=choice['message'].get('content') or ''
        record['finish_reason']=choice.get('finish_reason')
        if choice.get('finish_reason')!='stop' or not text.strip():
            record['erro']='Resposta vazia ou incompleta; nao sera reexecutada para selecionar uma melhor'
        else:
            code=extract(text)
            (folder/'amostra.py').write_bytes(code.encode())
            record['codigo_sha256']=hashlib.sha256(code.encode()).hexdigest()
            try:ast.parse(code)
            except SyntaxError:record['erro']='SyntaxError no codigo retornado'
    record['concluida_em']=now();save(file,record)
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--executar',action='store_true',help='faz no maximo oito geracoes pagas e avalia no Docker')
    args=p.parse_args()
    frozen=plan()
    print('Plano registrado:',len(frozen['jobs']),'geracoes; imagem',frozen['imagem'],flush=True)
    if not args.executar:return
    rows=[]
    for job in frozen['jobs']:
        record=collect(job,frozen)
        folder=DATA/job['id'];output=folder/'avaliacao.json'
        if not output.exists():
            if record['erro']:
                evaluated=dict(estado='inconclusivo',erro=record['erro'],testes=[])
            else:
                assert image_id()==frozen['imagem']
                evaluated=run(['--amostra','/candidate/amostra.py'],folder/'amostra.py')
            save(output,evaluated)
        result=json.loads(output.read_text(encoding='utf-8'))
        functional=[t for t in result['testes'] if t['tipo']=='funcional']
        security=[t for t in result['testes'] if t['tipo']=='seguranca']
        state='inconclusivo' if not functional else 'aprovado' if all(t['status']=='aprovado' for t in functional) else 'reprovado'
        counts=Counter(t['status'] for t in security)
        rows.append(dict(id=job['id'],modelo=job['modelo'],nivel=job['nivel'],funcional=state,
                         seguranca=dict(counts),erro=record['erro'] or result.get('erro'),
                         uso=(record['resposta'] or {}).get('usage',{})))
        print(job['id'],job['modelo'],job['nivel'],'funcional='+state,'seguranca='+json.dumps(dict(counts)),flush=True)
    save(DATA/'resumo.json',dict(plano='plano.json',amostras=rows,encerrado_em=now()))
    lines=['# Coleta exploratória T04','',
           'Oito gerações novas, uma por nível e modelo. Esta coleta é separada do piloto e da amostra principal. Os critérios e a ordem foram registrados antes das chamadas.',
           '', '| Amostra | Modelo | Nível | Download funcional | Exposições | Abertura externa observada | Inconclusivos de segurança |',
           '|---|---|---|---|---:|---:|---:|']
    for r in rows:
        c=r['seguranca'];lines.append(f"| {r['id']} | {r['modelo']} | {r['nivel']} | {r['funcional']} | {c.get('exposicao',0)} | {c.get('acesso_externo_observado',0)} | {c.get('inconclusivo',0)} |")
    lines+=['','As contagens de exposição são casos de teste por geração, não gerações independentes. Uma única repetição por condição serve à validação do fluxo; não sustenta comparação estatística entre níveis.',
            '', 'Plano, respostas completas, tentativas, tokens e resultados: [dados/t04-exploratoria](../dados/t04-exploratoria).']
    (ROOT/'docs'/'T04-exploratoria.md').write_bytes(('\n'.join(lines)+'\n').encode())


if __name__=='__main__':main()
