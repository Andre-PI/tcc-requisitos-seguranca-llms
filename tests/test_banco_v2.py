import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import piloto
from t02_verificador import ESQUEMA
from t06_verificador import usuario_atual

INDICIOS = {
    'T01': ['hash', 'bcrypt', 'argon', 'limite', 'tentativa', 'enumera', 'temporiza', 'parametr'],
    'T02': ['vinculad', 'prepared', 'concatena', 'lista fechada', 'faixa', 'erros de banco'],
    'T06': ['pertence', 'dono', 'proprietario', 'autorizacao', 'outro usuario', 'exigir'],
}


def catalogo(tarefa):
    return json.loads((ROOT / f'tarefas/v2/{tarefa}.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('tarefa', sorted(INDICIOS))
def test_contrato_nao_entrega_defesa_ao_n0(tarefa):
    c = catalogo(tarefa)
    texto = (c['N0'] + ' ' + c['contrato_comum']).lower()
    assert not [i for i in INDICIOS[tarefa] if i in texto]


@pytest.mark.parametrize('tarefa', sorted(INDICIOS))
def test_enunciados_iguais_aos_do_piloto(tarefa):
    c, p = catalogo(tarefa), piloto.TAREFAS[tarefa]
    for campo in ('N0', 'N1', 'N2_extra', 'N3_extra'):
        assert c[campo] == p[campo]


def test_token_ficticio_identifica_usuario():
    assert usuario_atual('Bearer token-a-ficticio') == {'id': 10}
    assert usuario_atual('bearer token-b-ficticio') == {'id': 20}


@pytest.mark.parametrize('valor', [None, '', 'Bearer', 'Bearer invalido', 'token-a-ficticio'])
def test_token_invalido_e_recusado(valor):
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        usuario_atual(valor)


def test_segredo_existe_so_em_outra_tabela():
    assert 'CREATE TABLE segredos' in ESQUEMA
    assert 'segredos' not in catalogo('T02')['contrato_comum']
