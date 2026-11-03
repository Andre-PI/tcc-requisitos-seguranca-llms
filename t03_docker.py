"""Constrói e valida T03 sem alterar a imagem ou os registros T04."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import uuid
from t04_docker import command

ROOT=Path(__file__).resolve().parent
TAG='tcc-t03:validacao-2'


def build():
    folder=ROOT/'docker'/'t03'
    for name in ('t03_verificador.py','t03_referencias.py','t03_worker_linux.py'):
        shutil.copy2(ROOT/name,folder/name)
    subprocess.run(['docker','build','-t',TAG,str(folder)],check=True)


def image_id():
    return json.loads(subprocess.check_output(['docker','image','inspect',TAG,'--format','{{json .Id}}'],text=True))


def run(args=(),candidate=None,timeout=60):
    image=image_id()
    name='tcc-t03-'+uuid.uuid4().hex[:12]
    try:
        p=subprocess.run(command(image,name,args,candidate),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        lines=[s.split('TCC_RESULTADO_JSON:',1)[1] for s in p.stdout.splitlines() if s.startswith('TCC_RESULTADO_JSON:')]
        report=json.loads(lines[-1]) if lines else dict(estado='inconclusivo',erro='Executor sem resultado',testes=[])
        report.update(imagem=image,container_exit=p.returncode,stderr=p.stderr,stdout=p.stdout)
        return report
    except subprocess.TimeoutExpired:
        return dict(estado='inconclusivo',erro='Timeout do conteiner',testes=[],imagem=image)
    finally:subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)


def validar():
    probe=run(['--probe'])
    assert len(probe.get('confinamento',{}))==5 and all(probe['confinamento'].values()),'Falha no probe do conteiner'
    report=run();report['probe']=probe
    files=['tarefas/T03.json','t03_verificador.py','t03_referencias.py','t03_worker_linux.py','t03_docker.py','docker/t03/Dockerfile','docker/t03/requirements.txt']
    report['arquivos']={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
    (ROOT/'docs'/'T03-validacao-linux.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    if report['container_exit'] or report['expectativas_atendidas']!=report['referencias']:raise RuntimeError('Controles T03 falharam; consultar relatorio')
    print(f"T03: {report['expectativas_atendidas']}/{report['referencias']} controles atendidos; imagem {report['imagem']}")


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');p.add_argument('--validar',action='store_true');args=p.parse_args()
    if args.build:build()
    if args.validar:validar()
