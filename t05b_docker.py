"""Constroi e valida o instrumento T05b sem alterar a imagem ou os registros da T05."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import uuid
from t04_docker import command

ROOT = Path(__file__).resolve().parent
TAG = 'tcc-t05b:validacao-1'
COPIAS = ['t05_infra.py', 't05_referencias.py', 't05_verificador.py', 't05_worker_linux.py', 't05b_worker_linux.py']
SOURCES = ['tarefas/v2/T05b.json', *COPIAS, 't05b_docker.py', 't04_docker.py', 'docker/t05b/Dockerfile', 'docker/t05b/requirements.txt']


def image_id():
    return json.loads(subprocess.check_output(['docker', 'image', 'inspect', TAG, '--format', '{{json .Id}}'], text=True))


def build():
    for nome in COPIAS:
        shutil.copy2(ROOT / nome, ROOT / 'docker/t05b' / nome)
    subprocess.run(['docker', 'build', '-t', TAG, str(ROOT / 'docker/t05b')], check=True)


def run(args=(), candidate=None, timeout=60):
    image = image_id()
    name = 'tcc-t05b-' + uuid.uuid4().hex[:12]
    try:
        p = subprocess.run(command(image, name, args, candidate), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        lines = [s.split('TCC_RESULTADO_JSON:', 1)[1] for s in p.stdout.splitlines() if s.startswith('TCC_RESULTADO_JSON:')]
        r = json.loads(lines[-1]) if lines else dict(estado='inconclusivo', erro='Executor sem resultado', testes=[])
        r.update(imagem=image, container_exit=p.returncode, stdout=p.stdout, stderr=p.stderr)
        return r
    except subprocess.TimeoutExpired:
        return dict(imagem=image, estado='inconclusivo', erro='Timeout do conteiner', testes=[])
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=15)


def validar():
    probe = run(['--probe'])
    assert len(probe.get('confinamento', {})) == 4 and all(probe['confinamento'].values()), 'Probe T05b falhou'
    r = run()
    r['probe'] = probe
    r['arquivos'] = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
    (ROOT / 'docs/T05b-validacao-linux.json').write_bytes((json.dumps(r, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    assert r['container_exit'] == 0 and r['referencias'] == r['expectativas_atendidas'] == 11, 'Controles T05b falharam; consultar relatorio'
    print('T05b: 11/11 controles atendidos; imagem', r['imagem'])


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--build', action='store_true')
    p.add_argument('--validar', action='store_true')
    args = p.parse_args()
    if args.build:
        build()
    if args.validar:
        validar()
