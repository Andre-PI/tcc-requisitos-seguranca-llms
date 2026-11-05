"""Emenda 02: valida a v5 da T03 e reavalia as geracoes coletadas, sem novas chamadas a modelos."""
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
sys.path.insert(0, str(ROOT / 'instrumentos_v3'))
from t04_docker import command
from validar import run

TAG = 'tcc-t03:grupos-v5'
AQUI = Path(__file__).parent
DATA = ROOT / 'dados/coleta-principal'
EXTENSOES = {'extensao_dupla', 'extensao_html'}
CONTROLES = {'grava_uuid.py': 'aprovado', 'grava_php.py': 'reprovado', 'rejeita.py': 'aprovado'}


def avaliar(image, amostra):
    nome = 'tcc-t03v5-' + uuid.uuid4().hex[:10]
    p = subprocess.run(command(image, nome, ['--amostra', '/candidate/amostra.py'], amostra), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    linhas = [l.split(':', 1)[1] for l in p.stdout.splitlines() if l.startswith('TCC_RESULTADO_JSON:')]
    r = json.loads(linhas[-1]) if linhas else dict(estado='inconclusivo', erro='Executor sem resultado', testes=[])
    r.update(imagem=image, container_exit=p.returncode)
    return r


def main():
    base = subprocess.check_output(['docker', 'image', 'inspect', 'tcc-t03:grupos-v4', '--format', '{{.Id}}'], text=True).strip()
    (ROOT / 'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='build-t03v5-', dir=ROOT / 'tmp') as pasta:
        shutil.copy2(AQUI / 't03_verificador.py', pasta)
        (Path(pasta) / 'Dockerfile').write_text('FROM tcc-t03:grupos-v4\nCOPY t03_verificador.py /runner/\n', encoding='utf-8')
        subprocess.run(['docker', 'build', '--network=none', '--pull=false', '-t', TAG, pasta], check=True, capture_output=True)
    image = subprocess.check_output(['docker', 'image', 'inspect', TAG, '--format', '{{.Id}}'], text=True).strip()
    probe = run(image, ['--probe'])
    assert all(probe['confinamento'].values()), 'Falha no confinamento'
    referencias = run(image)
    assert referencias['referencias'] == referencias['expectativas_atendidas'] == 9, 'Referencias anteriores falharam'
    regressao = run(image, ['/runner/regressao_linux.py', 'T03'], entrada='python')
    assert regressao['referencias'] == regressao['expectativas_atendidas'] == 4, 'Controles anteriores falharam'
    controles = {}
    for arquivo, esperado in CONTROLES.items():
        r = avaliar(image, AQUI / 'controles' / arquivo)
        status = {t['teste']: t['status'] for t in r['testes']}
        assert r['controles_positivos'], arquivo
        assert all(status[c] == esperado for c in EXTENSOES), (arquivo, status)
        controles[arquivo] = {c: status[c] for c in EXTENSOES}
    destino = DATA / 'reavaliacao-t03-v5'
    destino.mkdir(exist_ok=True)
    mudancas = []
    jobs = [j for j in json.loads((DATA / 'plano.json').read_text(encoding='utf-8'))['jobs'] if j['tarefa'] == 'T03']
    for job in jobs:
        amostra = DATA / job['id'] / 'amostra.py'
        original = json.loads((DATA / job['id'] / 'avaliacao.json').read_text(encoding='utf-8'))
        if not amostra.exists():
            (destino / f"{job['id']}.json").write_bytes((json.dumps(original, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            continue
        novo = avaliar(image, amostra)
        antes = {t['teste']: t['status'] for t in original.get('testes', [])}
        depois = {t['teste']: t['status'] for t in novo.get('testes', [])}
        diferencas = {k: [antes.get(k), depois.get(k)] for k in set(antes) | set(depois) if antes.get(k) != depois.get(k)}
        assert set(diferencas) <= EXTENSOES, ('Mudanca fora dos casos previstos', job['id'], diferencas)
        assert all(v == ['reprovado', 'aprovado'] for v in diferencas.values()), (job['id'], diferencas)
        (destino / f"{job['id']}.json").write_bytes((json.dumps(novo, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        if diferencas:
            mudancas.append(dict(id=job['id'], modelo=job['modelo'], nivel=job['nivel'], casos=sorted(diferencas)))
    fontes = [AQUI / 't03_verificador.py', Path(__file__), *sorted((AQUI / 'controles').glob('*.py')), ROOT / 'analise_emenda02.py']
    relatorio = dict(versao='instrumentos-5', tarefa='T03', imagem=image, imagem_base=base, probe=probe, referencias=referencias, regressao=regressao, controles_extensao=controles, geracoes_reavaliadas=len(jobs), geracoes_alteradas=mudancas,
                     arquivos={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes})
    (ROOT / 'docs/instrumentos-v5').mkdir(exist_ok=True)
    (ROOT / 'docs/instrumentos-v5/T03-validacao-linux.json').write_bytes((json.dumps(relatorio, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print('T03 v5: 9 referencias, 4 controles e', len(controles), 'controles de extensao atendidos;', len(jobs), 'reavaliadas;', len(mudancas), 'alteradas')


if __name__ == '__main__':
    main()
