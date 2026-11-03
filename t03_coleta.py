"""Coleta exploratoria T03, registrada antes das chamadas e separada do piloto."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import t04_coleta as api
from t03_docker import image_id,run

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'dados'/'t03-exploratoria'
SOURCES=['tarefas/T03.json','t03_verificador.py','t03_referencias.py','t03_worker_linux.py','t03_docker.py','t03_coleta.py','t04_coleta.py','t04_docker.py','docker/t03/Dockerfile','docker/t03/requirements.txt','docs/T03-protocolo.md']


def prompt(nivel):
    c=json.loads((ROOT/'tarefas/T03.json').read_text(encoding='utf-8'))
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
    v=json.loads((ROOT/'docs/T03-validacao-linux.json').read_text(encoding='utf-8'))
    assert v['referencias']==v['expectativas_atendidas']==9 and v['imagem']==image_id()
    assert len(v['probe']['confinamento'])==5 and all(v['probe']['confinamento'].values())
    for n,sha in v['arquivos'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==sha
    jobs=[dict(modelo=m,nivel=n,repeticao=1) for m in api.MODELS for n in ['N0','N1','N2','N3']]
    random.Random(2026110303).shuffle(jobs)
    for i,j in enumerate(jobs,1):j.update(id=f't03-{i:02d}',prompt=prompt(j['nivel']))
    frozen=dict(versao='t03-exploratoria-1',registrado_em=api.now(),natureza='Exploratoria; oito geracoes fora do piloto e das 800 principais',
                semente_ordem=2026110303,jobs=jobs,imagem=image_id(),fontes_sha256=fingerprints(),
                parametros={'temperature':0.7,'max_completion_tokens':1500,'store':False},
                retentativas='Ate duas tentativas em erro transitorio; nao regenerar por resultado funcional. Transporte interrompido pode ter sido processado no servidor; tentativas preservadas.',
                criterios='docs/T03-protocolo.md; todas as respostas, truncamentos e falhas preservados')
    api.save(file,frozen);return frozen


def summarize(record,result):
    tests=result.get('testes',[])
    functional=[t for t in tests if t['tipo']=='funcional']
    counts=Counter(t['status'] for t in tests if t['tipo'].startswith('seguranca_'))
    state='inconclusivo' if not functional else 'aprovado' if all(t['status']=='aprovado' for t in functional) else 'reprovado'
    return dict(id=record['id'],modelo=record['modelo'],nivel=record['nivel'],funcional=state,seguranca=dict(counts),
                contrato={t['teste']:t['status'] for t in tests if t['tipo'] in ('contrato','integridade')},
                erro=record['erro'] or result.get('erro'),uso=(record['resposta'] or {}).get('usage',{}))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--executar',action='store_true');args=p.parse_args()
    frozen=plan();print('Plano T03 registrado: oito geracoes; imagem',frozen['imagem'],flush=True)
    if not args.executar:return
    api.DATA=DATA  # Reutiliza somente a persistencia e o cliente, sem modificar fontes da T04.
    rows=[]
    for job in frozen['jobs']:
        record=api.collect(job,frozen);folder=DATA/job['id'];output=folder/'avaliacao.json'
        if not output.exists():
            assert image_id()==frozen['imagem']
            result=dict(estado='inconclusivo',erro=record['erro'],testes=[]) if record['erro'] else run(['--amostra','/candidate/amostra.py'],folder/'amostra.py')
            api.save(output,result)
        result=json.loads(output.read_text(encoding='utf-8'));row=summarize(record,result);rows.append(row)
        print(job['id'],job['modelo'],job['nivel'],'funcional='+row['funcional'],'seguranca='+json.dumps(row['seguranca']),flush=True)
    api.save(DATA/'resumo.json',dict(plano='plano.json',amostras=rows,encerrado_em=api.now()))
    lines=['# Coleta exploratória T03','','Oito gerações, uma por nível e modelo, em ordem sorteada registrada antes das chamadas. Separadas das 72 gerações do piloto e da coleta principal.','',
           '| Amostra | Modelo | Nível | Uploads legítimos | Casos de segurança reprovados | Inconclusivos de segurança |','|---|---|---|---|---:|---:|']
    for r in rows:lines.append(f"| {r['id']} | {r['modelo']} | {r['nivel']} | {r['funcional']} | {r['seguranca'].get('reprovado',0)} | {r['seguranca'].get('inconclusivo',0)} |")
    lines+=['','As contagens referem-se a casos por geração, não a amostras independentes. Reprovação de requisito não comprova exploração em produção. Respostas, tentativas, tokens, prompts e resultados estão em [dados/t03-exploratoria](../dados/t03-exploratoria). Uma repetição por condição não sustenta comparação estatística entre níveis.']
    (ROOT/'docs/T03-exploratoria.md').write_bytes(('\n'.join(lines)+'\n').encode('utf-8'))


if __name__=='__main__':main()
