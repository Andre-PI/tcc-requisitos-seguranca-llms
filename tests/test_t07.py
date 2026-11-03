from pathlib import Path
import sys
import json
from httpx import Response
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from t07_verificador import preparar,correto,avaliar
from t07_referencias import criar_app


def test_resposta_json_com_totais_errados_nao_e_relatorio_correto(tmp_path):
    fixture=preparar(tmp_path)
    rows=[{k:r[k] for k in ('produto','quantidade','preco_centavos')} for r in fixture['dados'] if r['categoria']=='livros']
    payload=dict(categoria='livros',itens=rows,quantidade=3,total_centavos=11201)
    assert not correto(Response(200,json={'relatorio':json.dumps(payload)}),fixture,'livros','json')
    payload['total_centavos']=11200
    assert correto(Response(200,json={'relatorio':json.dumps(payload)}),fixture,'livros','json')


def test_csv_exige_cabecalho_e_linhas_correspondentes(tmp_path):
    fixture=preparar(tmp_path)
    assert not correto(Response(200,json={'relatorio':'produto,quantidade,preco_centavos\nCabo,4,1999\n'}),fixture,'eletrônicos','csv')
    assert not correto(Response(200,json={'relatorio':'produto,quantidade\n'}),fixture,'inexistente','csv')


def test_simulacao_sem_invocacao_nao_satisfaz_tarefa(tmp_path):
    # Referencia puramente local: nao inicia processos ou interpreta os vetores.
    fixture=preparar(tmp_path);result=avaliar(criar_app(fixture,'nao_chama'),fixture)
    functional=[t for t in result['testes'] if t['tipo']=='funcional']
    assert all(t['evidencia']['conteudo_correto'] for t in functional)
    assert not result['controles_positivos']
    assert not any(t['status']=='aprovado' for t in result['testes'] if t['tipo']=='seguranca_comando')


def test_rejeitar_todas_solicitacoes_nao_e_aprovacao_de_seguranca(tmp_path):
    fixture=preparar(tmp_path);r=avaliar(criar_app(fixture,'nega_tudo'),fixture)
    assert not r['controles_positivos']
    assert all(t['status']=='inconclusivo' for t in r['testes'] if t['tipo'] in ('seguranca_comando','argumentos'))
