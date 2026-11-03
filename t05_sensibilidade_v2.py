"""Reexecuta os mesmos codigos em condicoes diagnosticas, sem chamar a API."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import uuid
import t04_coleta as storage
from t04_docker import command
from t05_docker import image_id as original_image
from t05_coleta import summarize

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'dados/t05-sensibilidade-v2'
TAG='tcc-t05:sensibilidade-2'


def image_id():return json.loads(subprocess.check_output(['docker','image','inspect',TAG,'--format','{{json .Id}}'],text=True))


def run(args,candidate=None):
    name='tcc-t05-diag-'+uuid.uuid4().hex[:12]
    try:
        p=subprocess.run(command(image_id(),name,args,candidate),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        lines=[s.split('TCC_RESULTADO_JSON:',1)[1] for s in p.stdout.splitlines() if s.startswith('TCC_RESULTADO_JSON:')]
        result=json.loads(lines[-1]) if lines else dict(estado='inconclusivo',erro='Executor sem resultado',testes=[])
        result.update(imagem=image_id(),container_exit=p.returncode,stdout=p.stdout,stderr=p.stderr);return result
    except subprocess.TimeoutExpired:return dict(imagem=image_id(),estado='inconclusivo',erro='Timeout do conteiner',testes=[])
    finally:subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)


def main():
    p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');args=p.parse_args()
    original=json.loads((ROOT/'dados/t05-exploratoria/plano.json').read_text(encoding='utf-8'))
    assert original_image()==original['imagem']
    prior=json.loads((ROOT/'dados/t05-sensibilidade/plano.json').read_text(encoding='utf-8'))
    base=json.loads(subprocess.check_output(['docker','image','inspect','tcc-t05:sensibilidade-1','--format','{{json .Id}}'],text=True))
    assert base==prior['imagem']
    if args.build:
        shutil.copy2(ROOT/'t05_sensibilidade_worker_v2.py',ROOT/'docker/t05-sensibilidade-v2/t05_sensibilidade_worker_v2.py')
        subprocess.run(['docker','build','-t',TAG,str(ROOT/'docker/t05-sensibilidade-v2')],check=True)
    sources=['t05_sensibilidade_v2.py','t05_sensibilidade_worker_v2.py','docker/t05-sensibilidade-v2/Dockerfile']
    frozen=dict(registrado_em=storage.now(),natureza='Diagnostico pos-coleta; nao substitui resultados originais e nao gera novas respostas',imagem=image_id(),imagem_original=original['imagem'],imagem_diagnostica_base=base,correcao='Atualiza tambem o email padrao de solicitar; v1 dependencia_e_dominio preservada como diagnostico com adaptador incompleto',fontes_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sources},condicoes={'dependencia':[], 'dependencia_e_dominio':['--dominio-example']})
    file=DATA/'plano.json'
    if file.exists():
        old=json.loads(file.read_text(encoding='utf-8'))
        assert old['fontes_sha256']==frozen['fontes_sha256'] and old['imagem']==frozen['imagem']
    else:storage.save(file,frozen)
    probe=run(['--probe']);email=run(['--verificar-email'])
    assert len(probe['confinamento'])==4 and all(probe['confinamento'].values())
    assert email['alice@example.test']=='rejeitado' and email['alice@example.com']=='aceito'
    storage.save(DATA/'probe.json',dict(confinamento=probe,validacao_email=email))
    refs=run([]);assert refs['expectativas_atendidas']==refs['referencias']==11
    storage.save(DATA/'referencias.json',refs)
    rows=[]
    for condition,flags in frozen['condicoes'].items():
        for job in original['jobs']:
            folder=ROOT/'dados/t05-exploratoria'/job['id'];g=json.loads((folder/'geracao.json').read_text(encoding='utf-8'))
            file=DATA/condition/job['id']/'avaliacao.json'
            if not file.exists():
                assert hashlib.sha256((folder/'amostra.py').read_bytes()).hexdigest()==g['codigo_sha256']
                result=run(flags+['--amostra','/candidate/amostra.py'],folder/'amostra.py');storage.save(file,result)
            result=json.loads(file.read_text(encoding='utf-8'));row=summarize(g,result);row['condicao']=condition;rows.append(row)
            print(condition,job['id'],row['funcional'],row['erro'] or '',flush=True)
    storage.save(DATA/'resumo.json',dict(amostras=rows,encerrado_em=storage.now(),novas_chamadas_api=0))


if __name__=='__main__':main()
