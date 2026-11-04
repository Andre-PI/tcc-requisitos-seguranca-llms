from collections import Counter
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import analise_principal as a
import coleta_principal as c


def caso(nome, status='aprovado', tipo='seguranca'):
    return dict(teste=nome, tipo=tipo, status=status)


def test_desenho_tem_800_geracoes_balanceadas():
    jobs = c.montar_jobs()
    assert len(jobs) == 800 and len({j['id'] for j in jobs}) == 800
    assert set(Counter((j['tarefa'], j['modelo'], j['nivel']) for j in jobs).values()) == {10}
    assert set(Counter(j['nivel'] for j in jobs).values()) == {200}
    assert jobs == c.montar_jobs()
    assert 'email-validator 2.3.0' in next(j for j in jobs if j['tarefa'] == 'T05')['prompt']


def test_sorteio_de_revisao_cobre_cada_combinacao():
    jobs = c.montar_jobs()
    escolhidas = a.amostra_revisao(jobs)
    por_id = {j['id']: j for j in jobs}
    assert len(escolhidas) == 80
    assert len({(por_id[i]['tarefa'], por_id[i]['modelo'], por_id[i]['nivel']) for i in escolhidas}) == 80
    assert escolhidas == a.amostra_revisao(jobs)


def test_limite_de_tokens_e_igual_nos_provedores():
    assert c.PARAMETROS[c.GPT]['max_completion_tokens'] == c.PARAMETROS[c.GEMINI]['maxOutputTokens'] == 4000
    assert c.PARAMETROS[c.GPT]['temperature'] == c.PARAMETROS[c.GEMINI]['temperature']
    assert c.PARAMETROS[c.GEMINI]['thinkingConfig'] == {'thinkingBudget': 0}


def test_interpretar_resposta_do_openai():
    r = {'model': c.GPT, 'choices': [{'finish_reason': 'stop', 'message': {'content': 'x=1'}}]}
    assert c.interpretar(c.GPT, r) == ('x=1', 'stop', c.GPT, None)
    r['choices'][0]['finish_reason'] = 'length'
    assert c.interpretar(c.GPT, r)[3]


@pytest.mark.parametrize('casos,esperado', [
    ([caso('a'), caso('b')], 'aprovada'),
    ([caso('a'), caso('b', 'reprovado')], 'falha'),
    ([caso('a'), caso('b', 'inconclusivo')], 'sem_falha_parcial'),
    ([caso('a', 'inconclusivo'), caso('b', 'inconclusivo')], 'inconclusiva'),
    ([caso('a', 'inconclusivo'), caso('b', 'reprovado')], 'falha'),
    ([], 'inconclusiva'),
    ([caso('a', 'exposicao')], 'falha'),
    ([caso('a', 'acesso_externo_observado')], 'falha'),
    ([caso('a'), caso('b', 'nao_executado')], 'aprovada'),
    ([caso('a', 'reprovado', 'robustez'), caso('b')], 'aprovada'),
    ([caso('a', 'reprovado', 'seguranca_xss')], 'falha'),
    ([caso('a', 'reprovado', 'argumentos')], 'falha'),
])
def test_desfecho_de_seguranca(casos, esperado):
    assert a.desfecho_seguranca('T09', dict(testes=casos, controles_positivos=True)) == esperado


def test_sem_controle_base_so_a_falha_observada_conta():
    assert a.desfecho_seguranca('T09', dict(testes=[caso('a')], controles_positivos=False)) == 'inconclusiva'
    assert a.desfecho_seguranca('T09', dict(testes=[caso('a', 'reprovado')], controles_positivos=False)) == 'falha'


def test_valores_declarados_so_em_n3_ficam_fora_do_desfecho():
    t05 = dict(testes=[caso('token_reutilizado'), caso('validade:900', 'reprovado'), caso('validade:901', 'reprovado')], controles_positivos=True)
    assert a.desfecho_seguranca('T05', t05) == 'aprovada'
    assert a.desfecho_seguranca('T01', t05) == 'falha'
    t05['testes'].append(caso('expira_em_uma_semana', 'reprovado'))
    assert a.desfecho_seguranca('T05', t05) == 'falha'
    t03 = dict(testes=[caso('svg'), caso('excesso_bytes', 'reprovado', 'seguranca_conteudo'), caso('excesso_dimensoes', 'reprovado', 'seguranca_conteudo')], controles_positivos=True)
    assert a.desfecho_seguranca('T03', t03) == 'aprovada'


def test_funcional_em_tarefa_sem_grupos():
    r = dict(testes=[caso('a', 'aprovado', 'funcional'), caso('b', 'reprovado', 'funcional')])
    assert a.desfecho_funcional(r, 'N0') == ('reprovado', 'reprovado')
    assert a.desfecho_funcional(dict(testes=[]), 'N0') == ('inconclusivo', 'inconclusivo')


def test_funcional_com_grupos_usa_o_nivel():
    r = dict(testes=[], grupos_funcionais=dict(base=dict(status='aprovado'), detalhado=dict(status='reprovado')))
    assert a.desfecho_funcional(r, 'N0') == ('aprovado', 'aprovado')
    assert a.desfecho_funcional(r, 'N1') == ('reprovado', 'aprovado')


def test_wilson():
    baixo, alto = a.wilson(0, 10)
    assert baixo == 0 and alto == pytest.approx(0.2775, abs=0.001)
    assert a.wilson(5, 10) == pytest.approx((0.2366, 0.7634), abs=0.001)
    assert a.wilson(0, 0) == (None, None)


def test_cmh_sem_diferenca_nao_e_significativo():
    r = a.cmh([(5, 5, 5, 5), (3, 7, 3, 7)])
    assert r['p'] == pytest.approx(1.0) and r['razao_de_chances'] == pytest.approx(1.0)


def test_cmh_ignora_estratos_sem_variacao():
    r = a.cmh([(10, 0, 10, 0), (0, 10, 0, 10)])
    assert r['p'] is None and r['estratos_informativos'] == 0


def test_cmh_com_efeito_em_um_sentido():
    r = a.cmh([(9, 1, 2, 8), (8, 2, 1, 9), (7, 3, 2, 8)])
    assert r['p'] < 0.001 and r['razao_de_chances'] > 10 and r['ic95'][0] > 1


def test_holm_preserva_ordem_e_monotonia():
    assert a.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert a.holm([None, 0.02]) == [None, 0.02]
    assert a.holm([0.9, 0.8]) == pytest.approx([1.0, 1.0])


def test_analise_completa_com_dados_sinteticos():
    linhas = []
    for tarefa in ('T01', 'T02'):
        for modelo in ('m1', 'm2'):
            for nivel, falhas in (('N0', 8), ('N1', 7), ('N2', 5), ('N3', 1)):
                for i in range(10):
                    linhas.append(dict(id=f'{tarefa}{modelo}{nivel}{i}', tarefa=tarefa, modelo=modelo, nivel=nivel,
                                       seguranca='falha' if i < falhas else 'inconclusiva' if i == 9 else 'aprovada', funcional='aprovado', funcional_base='aprovado'))
    r = a.analisar(linhas)
    assert r['n'] == 160 and len(r['celulas']) == 16
    principal = {x['contraste']: x for x in r['seguranca']['QP2']['principal']}
    assert principal['N1-N3']['p_holm'] < 0.001 and principal['N1-N3']['razao_de_chances'] > 1
    assert r['seguranca']['QP2']['inconclusivas_por_nivel']['N3'] == 4
    assert r['QP3']['completo'][0]['p'] is None
