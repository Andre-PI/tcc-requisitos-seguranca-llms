from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import coleta_gemini as g


def resposta(texto='print(1)', motivo='STOP', pensamento=None):
    partes = [{'text': pensamento, 'thought': True}] if pensamento else []
    partes.append({'text': texto})
    return {'candidates': [{'finishReason': motivo, 'content': {'parts': partes}}]}


def test_resposta_completa_e_aceita():
    assert g.interpretar(resposta()) == ('print(1)', 'STOP', None)


def test_raciocinio_nao_entra_no_codigo():
    assert g.interpretar(resposta(pensamento='plano interno'))[0] == 'print(1)'


@pytest.mark.parametrize('dados', [resposta(motivo='MAX_TOKENS'), resposta(texto='  '), {'candidates': []}, {}])
def test_resposta_incompleta_e_registrada_como_erro(dados):
    assert g.interpretar(dados)[2]


def test_raciocinio_desativado_e_limite_da_coleta():
    assert g.PARAMETROS['thinkingConfig'] == {'thinkingBudget': 0}
    assert g.PARAMETROS['maxOutputTokens'] == 4000


def test_prompts_usam_catalogo_revisado_de_cada_tarefa():
    assert 'email-validator 2.3.0' in g.prompt('T05c', 'N0')
    assert 'TCC_ARQUIVOS_DIR' in g.prompt('T04', 'N0')
    assert len(g.TAREFAS) == 10 and set(g.V3) | set(g.V2) == set(g.TAREFAS)
