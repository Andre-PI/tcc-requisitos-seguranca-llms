"""Orquestra o contêiner T04, com limites e remoção após cada execução."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from validar_t04 import expectations

ROOT=Path(__file__).resolve().parent
TAG='tcc-t04:validacao-2'


def build():
    folder=ROOT/'docker'/'t04'
    # Somente os três arquivos necessários entram no contexto de build.
    for name in ['t04_verificador.py','t04_referencias.py','t04_worker_linux.py']:
        shutil.copy2(ROOT/name,folder/name)
    subprocess.run(['docker','build','-t',TAG,str(folder)],check=True)
    return image_id()


def image_id():
    return json.loads(subprocess.check_output(['docker','image','inspect',TAG,'--format','{{json .Id}}'],text=True))


def command(image,name,args,candidate=None):
    cmd=['docker','run','--rm','--pull=never','--name',name,'--network=none',
         '--read-only','--user','10001:10001','--cap-drop=ALL',
         '--security-opt=no-new-privileges=true','--memory=512m','--memory-swap=512m',
         '--cpus=1','--pids-limit=64','--tmpfs','/tmp:rw,nosuid,nodev,noexec,size=64m,mode=1777']
    if candidate is not None:
        path=Path(candidate).resolve()
        if not path.is_file() or ',' in str(path):raise ValueError('Caminho de amostra invalido')
        cmd+=['--mount',f'type=bind,source={path},target=/candidate/amostra.py,readonly']
    return cmd+[image]+list(args)


def run(args,candidate=None,timeout=45):
    name='tcc-t04-'+uuid.uuid4().hex[:12]
    image=image_id()
    cmd=command(image,name,args,candidate)
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        marked=[line.split('TCC_RESULTADO_JSON:',1)[1] for line in p.stdout.splitlines() if line.startswith('TCC_RESULTADO_JSON:')]
        result=json.loads(marked[-1]) if marked else dict(estado='inconclusivo',erro='Sem resultado do executor',testes=[])
        result.update(container_exit=p.returncode,imagem=image,stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired:
        result=dict(estado='inconclusivo',erro='Timeout do conteiner',testes=[],imagem=image)
    finally:
        assert re.fullmatch(r'tcc-t04-[0-9a-f]{12}',name)
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)
    return result


def validate():
    from t04_referencias import MODOS
    probe=run(['--probe'])
    if not all(probe.get('confinamento',{}).values()) or len(probe.get('confinamento',{}))!=5:
        raise RuntimeError('As verificacoes de confinamento falharam: '+json.dumps(probe))
    results=[]
    for mode in MODOS:
        result=run(['--referencia',mode])
        result['modo']=mode
        result['expectativa_atendida']=bool(result.get('link_disponivel') and expectations(mode,result))
        results.append(result)
    report=dict(imagem=image_id(),probe=probe,referencias=len(results),
                expectativas_atendidas=sum(x['expectativa_atendida'] for x in results),resultados=results,
                arquivos={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'t04_verificador.py',ROOT/'t04_referencias.py',ROOT/'t04_worker_linux.py',ROOT/'t04_docker.py',ROOT/'docker'/'t04'/'Dockerfile']})
    (ROOT/'docs'/'T04-validacao-linux.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    if report['expectativas_atendidas']!=len(results):raise RuntimeError('Falha nos controles Linux')
    print(f"Linux: {len(results)} referencias validadas, com links simbolicos; confinamento conferido.")
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--build',action='store_true')
    p.add_argument('--validar',action='store_true')
    args=p.parse_args()
    if args.build:build()
    if args.validar:validate()
