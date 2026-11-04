"""Valida a v4 de T03 e T04: 403 passa a contar como rejeicao nos casos de seguranca."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'instrumentos_v3'))
from t04_docker import command
from validar import run


def reavaliar(tag, imagem_v3, pasta):
    """Compara amostras coletadas nas duas versoes, sem chamar modelos nem alterar os registros."""
    linhas = []
    for job in json.loads((pasta / 'plano.json').read_text(encoding='utf-8'))['jobs']:
        amostra = pasta / job['id'] / 'amostra.py'
        if job.get('tarefa', tag) != tag or not amostra.exists():
            continue
        status = {}
        for rotulo, imagem in (('v3', imagem_v3), ('v4', image_id(tag))):
            p = subprocess.run(command(imagem, 'tcc-v4-' + job['id'] + '-' + rotulo, ['--amostra', '/candidate/amostra.py'], amostra), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
            r = [l.split(':', 1)[1] for l in p.stdout.splitlines() if l.startswith('TCC_RESULTADO_JSON:')]
            status[rotulo] = {t['teste']: t['status'] for t in json.loads(r[-1]).get('testes', [])} if r else {}
        mudancas = {k: [status['v3'].get(k), status['v4'].get(k)] for k in status['v4'] if status['v3'].get(k) != status['v4'].get(k)}
        linhas.append(dict(coleta=pasta.name, id=job['id'], nivel=job['nivel'], mudancas=mudancas))
    return linhas


def image_id(tarefa):
    return subprocess.check_output(['docker', 'image', 'inspect', f'tcc-{tarefa.lower()}:grupos-v4', '--format', '{{.Id}}'], text=True).strip()


def validar(tarefa):
    t = tarefa.lower()
    base = f'tcc-{t}:grupos-v3'
    imagem_v3 = subprocess.check_output(['docker', 'image', 'inspect', base, '--format', '{{.Id}}'], text=True).strip()
    verificador = ROOT / 'instrumentos_v4' / f'{t}_verificador.py'
    (ROOT / 'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='build-v4-', dir=ROOT / 'tmp') as pasta:
        pasta = Path(pasta)
        (pasta / f'{t}_verificador.py').write_bytes(verificador.read_bytes())
        (pasta / 'Dockerfile').write_text(f'FROM {base}\nCOPY {t}_verificador.py /runner/\n', encoding='utf-8')
        subprocess.run(['docker', 'build', '--network=none', '--pull=false', '-t', f'tcc-{t}:grupos-v4', str(pasta)], check=True, capture_output=True)
    imagem = image_id(tarefa)
    probe = run(imagem, ['--probe'])
    assert all(probe['confinamento'].values()), 'Falha no confinamento'
    if tarefa == 'T04':
        from t04_referencias import MODOS
        from validar_t04 import expectations
        linhas = []
        for modo in MODOS:
            r = run(imagem, ['--referencia', modo])
            r.update(modo=modo, expectativa_atendida=bool(expectations(modo, r) and r['link_disponivel']))
            linhas.append(r)
        referencias = dict(referencias=len(linhas), expectativas_atendidas=sum(r['expectativa_atendida'] for r in linhas), resultados=linhas)
    else:
        referencias = run(imagem)
    regressao = run(imagem, ['/runner/regressao_linux.py', tarefa], entrada='python')
    coletas = [ROOT / 'dados/gemini-exploratoria', ROOT / ('dados/t04-exploratoria' if tarefa == 'T04' else 'dados/t03-exploratoria-v2')]
    fontes = [verificador, Path(__file__), ROOT / 'instrumentos_v3/grupos_funcionais.py', ROOT / 'instrumentos_v3/regressao_linux.py']
    relatorio = dict(versao='instrumentos-4', tarefa=tarefa, imagem=imagem, imagem_base=imagem_v3, probe=probe, referencias=referencias, regressao=regressao,
                     reavaliacao_diagnostica=[l for c in coletas for l in reavaliar(tarefa, imagem_v3, c)],
                     arquivos={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes})
    destino = ROOT / 'docs/instrumentos-v4'
    destino.mkdir(exist_ok=True)
    (destino / f'{tarefa}-validacao-linux.json').write_bytes((json.dumps(relatorio, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    for grupo in (referencias, regressao):
        assert grupo['referencias'] == grupo['expectativas_atendidas'], f'Expectativas nao atendidas: {tarefa}'
    print(f"{tarefa}: {referencias['referencias']} referencias e {regressao['referencias']} controles atendidos", flush=True)
    for l in relatorio['reavaliacao_diagnostica']:
        if l['mudancas']:
            print(' ', l['coleta'], l['id'], l['nivel'], l['mudancas'], flush=True)


if __name__ == '__main__':
    for tarefa in ('T03', 'T04'):
        validar(tarefa)
