import io
import json
from pathlib import Path
import sys
import urllib.error
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import t04_coleta as coleta


def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(coleta,'DATA',tmp_path)
    monkeypatch.setattr(coleta,'api_key',lambda:'chave-ficticia-do-teste')
    return dict(id='teste',modelo='modelo-ficticio',nivel='N0',repeticao=1,prompt='prompt'),dict(parametros={'max_completion_tokens':1500,'temperature':0.7,'store':False})


def test_nao_repete_requisicao_interrompida(tmp_path,monkeypatch):
    job,plan=setup(tmp_path,monkeypatch)
    coleta.save(tmp_path/'teste'/'geracao.json',{'tentativas':[{'numero':1}]})
    monkeypatch.setattr(coleta.urllib.request,'urlopen',lambda *a,**k:pytest.fail('Nao deve haver nova chamada'))
    with pytest.raises(RuntimeError,match='interrompida'):coleta.collect(job,plan)


def test_truncamento_e_preservado_sem_regenerar(tmp_path,monkeypatch):
    job,plan=setup(tmp_path,monkeypatch)
    calls=[]
    class Response(io.BytesIO):
        status=200
        headers={'x-request-id':'teste'}
    def fake(req,**kwargs):
        calls.append(json.loads(req.data))
        return Response(json.dumps({'choices':[{'finish_reason':'length','message':{'content':'codigo parcial'}}]}).encode())
    monkeypatch.setattr(coleta.urllib.request,'urlopen',fake)
    r=coleta.collect(job,plan)
    assert r['erro'] and r['finish_reason']=='length'
    assert len(calls)==1 and calls[0]['max_completion_tokens']==1500
    assert not (tmp_path/'teste'/'amostra.py').exists()
    assert coleta.collect(job,plan)==r and len(calls)==1


def test_erro_http_permanente_fica_no_registro_sem_retentativa(tmp_path,monkeypatch):
    job,plan=setup(tmp_path,monkeypatch)
    def fake(*args,**kwargs):
        raise urllib.error.HTTPError('https://api.openai.com',400,'erro',{},io.BytesIO(b'parametro invalido'))
    monkeypatch.setattr(coleta.urllib.request,'urlopen',fake)
    r=coleta.collect(job,plan)
    assert r['erro'] and len(r['tentativas'])==1
    assert r['tentativas'][0]['http']==400
