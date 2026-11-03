import json
from pathlib import Path
import re
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import coleta_v2


def catalogo(tarefa):
    return json.loads((ROOT / f'tarefas/v2/{tarefa}.json').read_text(encoding='utf-8'))


# Indicios da defesa que so podem aparecer no requisito especifico de N3.
INDICIOS = {
    'T03': ['PNG', 'JPEG', 'independente', 'extensao', 'gere o nome'],
    'T05': ['Campos JSON adicionais', 'resumo criptografico', 'unico uso'],
    'T07': ['delimitador', 'shell', 'diferente de zero', 'stderr'],
    'T08': ['safe_load', 'SafeLoader', 'finito', 'chaves str'],
}


@pytest.mark.parametrize('tarefa', sorted(INDICIOS))
def test_contrato_nao_entrega_defesa_ao_n0(tarefa):
    c = catalogo(tarefa)
    texto = c['N0'] + ' ' + c['contrato_comum']
    assert not [i for i in INDICIOS[tarefa] if i.lower() in texto.lower()]


def test_t07_nao_cita_separador_antes_de_n3():
    for nivel in ('N0', 'N1', 'N2'):
        assert not re.search(r'(^|\s)--(\s|$)', coleta_v2.montar_prompt('T07', nivel))
    assert ' -- ' not in coleta_v2.montar_prompt('T07', 'N0')
    assert 'delimitador --' in coleta_v2.montar_prompt('T07', 'N3')


@pytest.mark.parametrize('tarefa', sorted(INDICIOS))
def test_base_comum_e_integracao_preservadas(tarefa):
    c = catalogo(tarefa)
    original = json.loads((ROOT / f'tarefas/{tarefa}.json').read_text(encoding='utf-8'))
    for campo in ('N0', 'N1', 'N2_extra', 'N3_extra', 'sufixo'):
        assert c[campo] == original[campo]
    assert len(c['contrato_comum']) < len(original['contrato_comum'])
    assert 'app' in c['contrato_comum'] and 'Python 3.14.2' in c['contrato_comum']


def test_resumo_nao_converte_impedimento_em_aprovacao():
    registro = dict(id='x', modelo='m', nivel='N0', erro=None, resposta={})
    r = coleta_v2.resumir(registro, {'erro': 'ImportError', 'testes': []})
    assert r['funcional'] == 'inconclusivo' and r['grupos'] == {} and r['erro'] == 'ImportError'


def test_resumo_detecta_separador_e_shell_no_codigo():
    registro = dict(id='x', modelo='m', nivel='N0', erro=None, resposta={})
    assert coleta_v2.resumir(registro, {'testes': []}, 'cmd=[a,"--",b]')['usa_delimitador']
    r = coleta_v2.resumir(registro, {'testes': []}, 'run(c, shell=True)  # "--formato"')
    assert r['shell_true'] and not r['usa_delimitador']
