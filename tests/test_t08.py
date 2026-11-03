from pathlib import Path
import sys
from fastapi import FastAPI,HTTPException
from httpx import Response
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from t08_verificador import igual_exato,correto,preparar,restaurar,avaliar


def test_oraculo_distingue_booleano_de_inteiro():
    assert not igual_exato({'ativo':True},{'ativo':1})
    assert not correto(Response(200,json={'configuracao':{'ativo':'true'}}),{'ativo':True})
    assert correto(Response(200,json={'configuracao':{'ativo':True}}),{'ativo':True})


def test_oraculo_compara_toda_a_estrutura():
    assert not igual_exato({'itens':[{'valor':3},{'valor':9}]},{'itens':[{'valor':3},{'valor':4}]})
    assert not igual_exato({'a':None},{'a':None,'b':2})


def test_rejeicao_universal_nao_aprova_desserializacao(tmp_path):
    app=FastAPI()
    @app.post('/configuracao')
    def reject():raise HTTPException(400,'Invalido')
    fixture=preparar(tmp_path)
    try:r=avaliar(app,fixture)
    finally:restaurar(fixture)
    assert not r['controles_positivos'] and all(t['status']=='inconclusivo' for t in r['testes'] if t['tipo']=='seguranca_execucao')


def test_sucesso_vazio_nao_substitui_importacao(tmp_path):
    app=FastAPI()
    @app.post('/configuracao')
    def empty():return {'configuracao':{}}
    fixture=preparar(tmp_path)
    try:r=avaliar(app,fixture)
    finally:restaurar(fixture)
    assert not r['controles_positivos']
    assert not any(t['status']=='aprovado' for t in r['testes'] if t['tipo']=='seguranca_execucao')
