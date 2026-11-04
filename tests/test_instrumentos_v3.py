import ast
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'instrumentos_v3'))
from grupos_funcionais import DETALHADOS, base_aprovada, grupo, registrar_grupos, resultado_funcional


def caso(nome, status='aprovado', tipo='funcional'):
    return dict(teste=nome, tipo=tipo, status=status)


def resultado(base, detalhado):
    testes = [caso('upload:foto.png', base), caso('preservacao_png', detalhado)]
    return dict(grupos_funcionais=registrar_grupos('T03', testes))


def test_grupos_e_nivel_exigido():
    assert grupo('T10', caso('consulta')) == 'detalhado'
    assert grupo('T10', caso('entrega')) == 'base'
    testes = [caso('entrega'), caso('consulta')]
    registrar_grupos('T10', testes)
    assert [t['exigido_desde'] for t in testes] == ['N0', 'N1']


def test_falha_detalhada_nao_bloqueia_controle_base():
    assert base_aprovada('T09', [caso('simples'), caso('acentos', 'reprovado')])
    assert not base_aprovada('T09', [caso('simples', 'reprovado'), caso('acentos')])


def test_base_ausente_nao_aprova_controle():
    assert not base_aprovada('T09', [])
    assert not base_aprovada('T09', [caso('acentos')])
    assert not base_aprovada('T09', [caso('simples', tipo='contrato')])


def test_falha_detalhada_so_reprova_a_partir_de_n1():
    r = resultado('aprovado', 'reprovado')
    assert resultado_funcional(r, 'N0')['status'] == 'aprovado'
    assert all(resultado_funcional(r, n)['status'] == 'reprovado' for n in ('N1', 'N2', 'N3'))


def test_falha_base_reprova_todos_os_niveis():
    r = resultado('reprovado', 'aprovado')
    assert all(resultado_funcional(r, n)['status'] == 'reprovado' for n in ('N0', 'N1', 'N2', 'N3'))


def test_sem_execucao_e_inconclusivo():
    assert all(resultado_funcional({}, n)['status'] == 'inconclusivo' for n in ('N0', 'N1', 'N2', 'N3'))
    with pytest.raises(ValueError):
        resultado_funcional({}, 'N4')


@pytest.mark.parametrize('tarefa', sorted(DETALHADOS))
def test_verificador_mantem_docstring_e_usa_grupos(tarefa):
    fonte = (ROOT / f'instrumentos_v3/{tarefa.lower()}_verificador.py').read_text(encoding='utf-8')
    assert ast.get_docstring(ast.parse(fonte))
    assert 'base_aprovada(' in fonte and 'registrar_grupos(' in fonte


def test_preservacao_t03_so_condiciona_casos_detalhados():
    linhas = (ROOT / 'instrumentos_v3/t03_verificador.py').read_text(encoding='utf-8').splitlines()
    usos = [l for l in linhas if "['gravado_valido']" in l]
    assert usos and all('base_ok' in l or 'preservacao_png' in l for l in usos)
