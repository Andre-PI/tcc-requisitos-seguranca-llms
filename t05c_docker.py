"""T05c: mesma imagem da T05b; o catalogo passa a declarar os campos JSON a todos os niveis."""
import hashlib
import json
from t05b_docker import COPIAS, ROOT, image_id, run

SOURCES = ['tarefas/v2/T05c.json', *COPIAS, 't05b_docker.py', 't05c_docker.py', 't04_docker.py', 'docker/t05b/Dockerfile', 'docker/t05b/requirements.txt']


def validar():
    probe = run(['--probe'])
    assert len(probe.get('confinamento', {})) == 4 and all(probe['confinamento'].values()), 'Probe T05c falhou'
    r = run()
    r['probe'] = probe
    r['arquivos'] = {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES}
    (ROOT / 'docs/T05c-validacao-linux.json').write_bytes((json.dumps(r, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    assert r['container_exit'] == 0 and r['referencias'] == r['expectativas_atendidas'] == 11, 'Controles T05c falharam; consultar relatorio'
    print('T05c: 11/11 controles atendidos; imagem', r['imagem'])


if __name__ == '__main__':
    validar()
