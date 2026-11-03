"""Orquestra a imagem compartilhada de T01, T02 e T06 e a validacao por referencias."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import uuid
from t04_docker import command

ROOT = Path(__file__).resolve().parent
TAG = 'tcc-banco-v2:validacao-1'
COPIAS = ['v2_banco.py', 'v2_worker_linux.py', 't01_verificador.py', 't01_referencias.py', 't02_verificador.py', 't02_referencias.py', 't06_verificador.py', 't06_referencias.py']
COMUNS = [*COPIAS, 'v2_instrumento.py', 't04_docker.py', 'docker/banco-v2/Dockerfile', 'docker/banco-v2/requirements.txt']


def image_id():
    return json.loads(subprocess.check_output(['docker', 'image', 'inspect', TAG, '--format', '{{json .Id}}'], text=True))


def build():
    for nome in COPIAS:
        shutil.copy2(ROOT / nome, ROOT / 'docker/banco-v2' / nome)
    subprocess.run(['docker', 'build', '-t', TAG, str(ROOT / 'docker/banco-v2')], check=True)


class Instrumento:
    def __init__(self, tarefa, referencias):
        self.tarefa, self.referencias = tarefa, referencias

    def image_id(self):
        return image_id()

    def run(self, args=(), candidate=None, timeout=180):
        image = image_id()
        name = f'tcc-{self.tarefa.lower()}-' + uuid.uuid4().hex[:12]
        try:
            p = subprocess.run(command(image, name, ['--tarefa', self.tarefa, *args], candidate), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
            lines = [s.split('TCC_RESULTADO_JSON:', 1)[1] for s in p.stdout.splitlines() if s.startswith('TCC_RESULTADO_JSON:')]
            r = json.loads(lines[-1]) if lines else dict(estado='inconclusivo', erro='Executor sem resultado', testes=[])
            r.update(imagem=image, container_exit=p.returncode, stdout=p.stdout, stderr=p.stderr)
            return r
        except subprocess.TimeoutExpired:
            return dict(imagem=image, estado='inconclusivo', erro='Timeout do conteiner', testes=[])
        finally:
            subprocess.run(['docker', 'rm', '-f', name], capture_output=True, timeout=15)

    def validar(self, timeout=500):
        probe = self.run(['--probe'])
        assert len(probe.get('confinamento', {})) == 4 and all(probe['confinamento'].values()), 'Probe falhou'
        r = self.run(timeout=timeout)
        r['probe'] = probe
        fontes = [f'tarefas/v2/{self.tarefa}.json', f'{self.tarefa.lower()}_docker.py', *COMUNS]
        r['arquivos'] = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in fontes}
        (ROOT / f'docs/{self.tarefa}-validacao-linux.json').write_bytes((json.dumps(r, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        assert r['container_exit'] == 0 and r['referencias'] == r['expectativas_atendidas'] == self.referencias, f'Controles {self.tarefa} falharam; consultar relatorio'
        print(f'{self.tarefa}: {self.referencias}/{self.referencias} controles atendidos; imagem', r['imagem'])
