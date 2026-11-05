import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4 = (ROOT / 'instrumentos_v4/t03_verificador.py').read_text(encoding='utf-8')
V5 = (ROOT / 'instrumentos_v5/t03_verificador.py').read_text(encoding='utf-8')


def test_v5_so_acrescenta_a_regra_de_extensao():
    linhas_v4 = V4.splitlines()
    novas = [l for l in V5.splitlines() if l not in linhas_v4]
    assert len(novas) == 7 and any("'extensao_dupla','extensao_html'" in l for l in novas)
    removidas = [l for l in linhas_v4 if l not in V5.splitlines()]
    assert removidas == ["            if wrote or 200<=r.status_code<300:status='reprovado'"]


def test_reavaliacao_so_mudou_os_casos_previstos():
    r = json.loads((ROOT / 'docs/instrumentos-v5/T03-validacao-linux.json').read_text(encoding='utf-8'))
    assert r['geracoes_reavaliadas'] == 80 and len(r['geracoes_alteradas']) == 33
    assert all(set(g['casos']) <= {'extensao_dupla', 'extensao_html'} for g in r['geracoes_alteradas'])
    assert r['controles_extensao']['grava_php.py'] == {'extensao_dupla': 'reprovado', 'extensao_html': 'reprovado'}
    assert r['controles_extensao']['grava_uuid.py'] == {'extensao_dupla': 'aprovado', 'extensao_html': 'aprovado'}
