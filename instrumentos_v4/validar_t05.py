"""Valida a v4 da T05: acrescenta o caso de token ainda aceito depois de uma semana."""
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

TAG = 'tcc-t05:grupos-v4'


def imagem():
    return subprocess.check_output(['docker', 'image', 'inspect', TAG, '--format', '{{.Id}}'], text=True).strip()


def status_da_amostra(image, amostra):
    p = subprocess.run(command(image, 'tcc-t05v4-' + amostra.parent.name, ['--amostra', '/candidate/amostra.py'], amostra), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
    r = [l.split(':', 1)[1] for l in p.stdout.splitlines() if l.startswith('TCC_RESULTADO_JSON:')]
    return {t['teste']: t['status'] for t in json.loads(r[-1]).get('testes', [])} if r else {}


def main():
    verificador = ROOT / 'instrumentos_v4/t05_verificador.py'
    base = 'tcc-t05b:validacao-1'
    imagem_base = subprocess.check_output(['docker', 'image', 'inspect', base, '--format', '{{.Id}}'], text=True).strip()
    (ROOT / 'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='build-t05v4-', dir=ROOT / 'tmp') as pasta:
        pasta = Path(pasta)
        (pasta / 't05_verificador.py').write_bytes(verificador.read_bytes())
        (pasta / 'Dockerfile').write_text(f'FROM {base}\nCOPY t05_verificador.py /runner/\n', encoding='utf-8')
        subprocess.run(['docker', 'build', '--network=none', '--pull=false', '-t', TAG, str(pasta)], check=True, capture_output=True)
    image = imagem()
    probe = run(image, ['--probe'])
    assert all(probe['confinamento'].values()), 'Falha no confinamento'
    referencias = run(image)
    casos = {r['modo']: {t['teste']: t['status'] for t in r['testes']} for r in referencias['resultados']}
    assert casos['protegida']['expira_em_uma_semana'] == 'aprovado', 'Referencia protegida reprovou o caso novo'
    assert casos['nao_expira']['expira_em_uma_semana'] == 'reprovado', 'Referencia sem expiracao nao foi detectada'
    assert casos['nega_tudo']['expira_em_uma_semana'] != 'aprovado', 'Rejeicao universal aprovada'
    reavaliacao = []
    for coleta, nome in (('dados/t05c-exploratoria-v2', 't05cv2'), ('dados/gemini-exploratoria', 'gem')):
        pasta = ROOT / coleta
        for job in json.loads((pasta / 'plano.json').read_text(encoding='utf-8'))['jobs']:
            amostra = pasta / job['id'] / 'amostra.py'
            if job.get('tarefa', 'T05c') == 'T05c' and amostra.exists():
                antigo = {t['teste']: t['status'] for t in json.loads((pasta / job['id'] / 'avaliacao.json').read_text(encoding='utf-8')).get('testes', [])}
                novo = status_da_amostra(image, amostra)
                reavaliacao.append(dict(coleta=pasta.name, id=job['id'], nivel=job['nivel'], expira_em_uma_semana=novo.get('expira_em_uma_semana'),
                                        validade_900=novo.get('validade:900'), outras_mudancas={k: [antigo.get(k), novo.get(k)] for k in novo if k != 'expira_em_uma_semana' and antigo.get(k) != novo.get(k)}))
    fontes = [verificador, Path(__file__)]
    relatorio = dict(versao='instrumentos-4', tarefa='T05', imagem=image, imagem_base=imagem_base, probe=probe, referencias=referencias, regressao=dict(referencias=0, expectativas_atendidas=0, resultados=[]),
                     reavaliacao_diagnostica=reavaliacao, arquivos={str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in fontes})
    destino = ROOT / 'docs/instrumentos-v4'
    (destino / 'T05-validacao-linux.json').write_bytes((json.dumps(relatorio, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    assert referencias['referencias'] == referencias['expectativas_atendidas'] == 11, 'Expectativas nao atendidas'
    print('T05 v4: 11 referencias atendidas; imagem', image)
    for l in reavaliacao:
        print(' ', l['coleta'], l['id'], l['nivel'], 'semana=' + str(l['expira_em_uma_semana']), '900=' + str(l['validade_900']), l['outras_mudancas'] or '')


if __name__ == '__main__':
    main()
