"""Valida os instrumentos v3 em imagens novas derivadas das imagens históricas locais."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from t04_docker import command

TAREFAS = ('T03', 'T04', 'T07', 'T08', 'T09', 'T10')


def run(image, args=(), entrada=None, timeout=180):
    name = 'tcc-grupos-v3-' + uuid.uuid4().hex[:12]
    cmd = command(image, name, args)
    if entrada:
        pos = cmd.index(image)
        cmd[pos:pos] = ['--entrypoint', entrada]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        linhas = [l.split(':', 1)[1] for l in p.stdout.splitlines() if l.startswith('TCC_RESULTADO_JSON:')]
        r = json.loads(linhas[-1]) if linhas else dict(erro='Sem resultado', stdout=p.stdout)
        r.update(container_exit=p.returncode, stderr=p.stderr)
        if p.returncode or 'erro' in r:
            raise RuntimeError(json.dumps(r, ensure_ascii=False))
        return r
    finally:
        subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=15)


def validar(tarefa, build=False):
    historico = json.loads((ROOT / f'docs/{tarefa}-validacao-linux.json').read_text(encoding='utf-8'))
    base = historico['imagem']
    tag = f'tcc-{tarefa.lower()}:grupos-v3'
    fontes = [ROOT / 'instrumentos_v3' / n for n in (f'{tarefa.lower()}_verificador.py', 'grupos_funcionais.py', 'regressao_linux.py', 'validar.py')]
    fontes += [ROOT / f'{tarefa.lower()}_referencias.py', ROOT / f'{tarefa.lower()}_worker_linux.py',
               ROOT / f'docs/{tarefa}-validacao-linux.json',
               ROOT / ('tarefas/T04.json' if tarefa == 'T04' else f'tarefas/v2/{tarefa}.json'),
               ROOT / 't04_docker.py']
    if tarefa == 'T04':
        fontes.append(ROOT / 'validar_t04.py')
    base_tag = f'tcc-{tarefa.lower()}:base-grupos-v3'
    dockerfile = f'FROM {base_tag}\nCOPY {tarefa.lower()}_verificador.py grupos_funcionais.py regressao_linux.py /runner/\n'
    if build:
        subprocess.run(['docker', 'tag', base, base_tag], check=True)
        observado = subprocess.check_output(['docker', 'image', 'inspect', base_tag, '--format', '{{.Id}}'], text=True).strip()
        if observado != base:
            raise RuntimeError('Imagem base difere do relatório histórico')
        (ROOT / 'tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='build-grupos-', dir=ROOT / 'tmp') as folder:
            folder = Path(folder)
            for p in fontes[:3]:
                shutil.copy2(p, folder / p.name)
            (folder / 'Dockerfile').write_text(dockerfile, encoding='utf-8')
            processo = subprocess.run(['docker', 'build', '--network=none', '--pull=false', '-t', tag, str(folder)],
                                      capture_output=True, text=True, encoding='utf-8', errors='replace')
            if processo.returncode:
                raise RuntimeError(processo.stderr)
    image = subprocess.check_output(['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'], text=True).strip()
    probe = run(image, ['--probe'])
    if len(probe.get('confinamento', {})) < 4 or not all(probe['confinamento'].values()):
        raise RuntimeError('Falha no confinamento')
    if tarefa == 'T04':
        from t04_referencias import MODOS
        from validar_t04 import expectations
        rows = []
        for modo in MODOS:
            r = run(image, ['--referencia', modo])
            r.update(modo=modo, expectativa_atendida=bool(expectations(modo, r) and r['link_disponivel']))
            rows.append(r)
        referencias = dict(referencias=len(rows), expectativas_atendidas=sum(r['expectativa_atendida'] for r in rows), resultados=rows)
    else:
        referencias = run(image)
    regressao = run(image, ['/runner/regressao_linux.py', tarefa], entrada='python')
    report = dict(versao='grupos-funcionais-3', tarefa=tarefa, imagem=image, imagem_base=base,
                  dockerfile=dockerfile, probe=probe, referencias=referencias, regressao=regressao,
                  arquivos={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes})
    folder = ROOT / 'docs/instrumentos-v3'
    folder.mkdir(exist_ok=True)
    (folder / f'{tarefa}-validacao-linux.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for grupo in (referencias, regressao):
        if grupo['referencias'] != grupo['expectativas_atendidas']:
            raise RuntimeError(f'Expectativas não atendidas: {tarefa}')
    print(f"{tarefa}: {referencias['referencias']} referências anteriores e {regressao['referencias']} controles novos atendidos", flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('tarefas', nargs='*', choices=TAREFAS, default=list(TAREFAS))
    p.add_argument('--build', action='store_true')
    args = p.parse_args()
    for tarefa in args.tarefas:
        validar(tarefa, args.build)
