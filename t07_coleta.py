"""Coleta exploratoria T07: plano previo e execucao de amostras somente no Docker."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import t04_coleta as api
from t07_docker import image_id,run

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'dados/t07-exploratoria'
SOURCES=['tarefas/T07.json','t07_utilitario.py','t07_verificador.py','t07_referencias.py','t07_worker_linux.py','t07_docker.py','t07_coleta.py','t04_coleta.py','t04_docker.py','docker/t07/Dockerfile','docker/t07/requirements.txt','docs/T07-protocolo.md','docs/T07-coleta-protocolo.md']


def prompt(nivel):
    c=json.loads((ROOT/'tarefas/T07.json').read_text(encoding='utf-8'))
    if nivel not in ('N0','N1','N2','N3'):raise ValueError(nivel)
    body=c['N0'] if nivel=='N0' else c['N1']
    if nivel in ('N2','N3'):body+=' '+c[nivel+'_extra']
    return '\n\n'.join([body,c['contrato_comum'],c['sufixo']])


def fingerprints():return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}


def plan():
    file=DATA/'plano.json'
    if file.exists():
        frozen=json.loads(file.read_text(encoding='utf-8'))
        assert frozen['fontes_sha256']==fingerprints(),'Fontes alteradas depois do plano'
        assert frozen['imagem']==image_id(),'Imagem alterada depois do plano'
        return frozen
    validation=json.loads((ROOT/'docs/T07-validacao-linux.json').read_text(encoding='utf-8'))
    assert validation['referencias']==validation['expectativas_atendidas']==10 and validation['imagem']==image_id()
    assert len(validation['probe']['confinamento'])==4 and all(validation['probe']['confinamento'].values())
    for name,sha in validation['arquivos'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    jobs=[dict(modelo=m,nivel=n,repeticao=1) for m in api.MODELS for n in ['N0','N1','N2','N3']]
    random.Random(2026110307).shuffle(jobs)
    for i,job in enumerate(jobs,1):job.update(id=f't07-{i:02d}',prompt=prompt(job['nivel']))
    frozen=dict(versao='t07-exploratoria-1',registrado_em=api.now(),natureza='Exploratoria; oito geracoes fora do piloto e das 800 principais',semente_ordem=2026110307,jobs=jobs,imagem=image_id(),fontes_sha256=fingerprints(),parametros={'temperature':0.7,'max_completion_tokens':1500,'store':False},retentativas='Ate duas tentativas em erro transitorio; nenhuma regeneracao por falha funcional, codigo invalido ou truncamento. Tentativas e falhas de transporte preservadas.',criterios='docs/T07-protocolo.md; docs/T07-coleta-protocolo.md')
    api.save(file,frozen);return frozen


def summarize(record,result):
    tests=result.get('testes',[]);functional=[t for t in tests if t['tipo']=='funcional']
    state='inconclusivo' if not functional else 'aprovado' if all(t['status']=='aprovado' for t in functional) else 'reprovado'
    return dict(id=record['id'],modelo=record['modelo'],nivel=record['nivel'],funcional=state,
                comandos=dict(Counter(t['status'] for t in tests if t['tipo']=='seguranca_comando')),
                argumentos=dict(Counter(t['status'] for t in tests if t['tipo']=='argumentos')),
                contrato={t['teste']:t['status'] for t in tests if t['tipo']=='contrato'},robustez={t['teste']:t['status'] for t in tests if t['tipo']=='robustez'},
                erro=record['erro'] or result.get('erro'),uso=(record['resposta'] or {}).get('usage',{}))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--executar',action='store_true');args=p.parse_args()
    frozen=plan();print('Plano T07 registrado: oito geracoes; imagem',frozen['imagem'],flush=True)
    if not args.executar:return
    api.DATA=DATA
    rows=[]
    for job in frozen['jobs']:
        record=api.collect(job,frozen);folder=DATA/job['id'];output=folder/'avaliacao.json'
        if not output.exists():
            assert image_id()==frozen['imagem']
            result=dict(estado='inconclusivo',erro=record['erro'],testes=[]) if record['erro'] else run(['--amostra','/candidate/amostra.py'],folder/'amostra.py')
            api.save(output,result)
        result=json.loads(output.read_text(encoding='utf-8'));row=summarize(record,result);rows.append(row)
        print(job['id'],job['modelo'],job['nivel'],'funcional='+row['funcional'],'comandos='+json.dumps(row['comandos']),'argumentos='+json.dumps(row['argumentos']),flush=True)
    api.save(DATA/'resumo.json',dict(plano='plano.json',amostras=rows,encerrado_em=api.now()))
    lines=['# Coleta exploratória T07','','Oito respostas planejadas, uma por nível e modelo. Prompts, ordem, fontes, imagem e parâmetros registrados antes das chamadas. Coleta separada do piloto e da amostra principal.','','| Amostra | Modelo | Nível | Relatórios legítimos | Comandos: reprovados / inconclusivos | Argumentos: reprovados / inconclusivos |','|---|---|---|---|---|---|']
    for r in rows:
        c=r['comandos'];a=r['argumentos'];lines.append(f"| {r['id']} | {r['modelo']} | {r['nivel']} | {r['funcional']} | {c.get('reprovado',0)} / {c.get('inconclusivo',0)} | {a.get('reprovado',0)} / {a.get('inconclusivo',0)} |")
    lines+=['','As contagens são casos dentro de cada geração, não amostras independentes. Injeção de argumentos é registrada à parte e não é somada automaticamente a CWE-78. Uma repetição por condição não sustenta comparação estatística. O uso de shell e a estrutura dos argumentos exigem revisão do código além dos casos comportamentais.','','Respostas completas, tentativas, tokens, prompts e avaliações: [dados/t07-exploratoria](../dados/t07-exploratoria).']
    (ROOT/'docs/T07-exploratoria.md').write_bytes(('\n'.join(lines)+'\n').encode())


if __name__=='__main__':main()
