"""Constroi o ambiente T07 e valida os controles de execucao externa."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import uuid
from t04_docker import command

ROOT=Path(__file__).resolve().parent
TAG='tcc-t07:validacao-1'
SOURCES=['tarefas/T07.json','t07_utilitario.py','t07_referencias.py','t07_verificador.py','t07_worker_linux.py','t07_docker.py','t04_docker.py','docker/t07/Dockerfile','docker/t07/requirements.txt']


def image_id():return json.loads(subprocess.check_output(['docker','image','inspect',TAG,'--format','{{json .Id}}'],text=True))


def build():
    for name in ['t07_utilitario.py','t07_referencias.py','t07_verificador.py','t07_worker_linux.py']:shutil.copy2(ROOT/name,ROOT/'docker/t07'/name)
    subprocess.run(['docker','build','-t',TAG,str(ROOT/'docker/t07')],check=True)


def run(args=(),candidate=None,timeout=60):
    image=image_id();name='tcc-t07-'+uuid.uuid4().hex[:12]
    try:
        p=subprocess.run(command(image,name,args,candidate),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        lines=[s.split('TCC_RESULTADO_JSON:',1)[1] for s in p.stdout.splitlines() if s.startswith('TCC_RESULTADO_JSON:')]
        result=json.loads(lines[-1]) if lines else dict(estado='inconclusivo',erro='Executor sem resultado',testes=[])
        result.update(imagem=image,container_exit=p.returncode,stdout=p.stdout,stderr=p.stderr);return result
    except subprocess.TimeoutExpired:return dict(imagem=image,estado='inconclusivo',erro='Timeout do conteiner',testes=[])
    finally:subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)


def validar():
    probe=run(['--probe']);assert len(probe.get('confinamento',{}))==4 and all(probe['confinamento'].values()),'Probe T07 falhou'
    report=run();report['probe']=probe
    report['arquivos']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCES}
    (ROOT/'docs/T07-validacao-linux.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    assert report['container_exit']==0 and report['referencias']==report['expectativas_atendidas']==10,'Controles T07 falharam; consultar relatorio'
    print('T07: 10/10 controles atendidos; imagem',report['imagem'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');p.add_argument('--validar',action='store_true');args=p.parse_args()
    if args.build:build()
    if args.validar:validar()
