import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import t03_coleta as coleta


def test_falha_de_importacao_nao_vira_protecao():
    record=dict(id='teste',modelo='ficticio',nivel='N0',erro=None,resposta={})
    row=coleta.summarize(record,dict(erro='ImportError',testes=[]))
    assert row['funcional']=='inconclusivo' and not row['seguranca'] and row['erro']=='ImportError'


def test_nao_mistura_colisao_funcional_com_casos_de_seguranca():
    record=dict(id='teste',modelo='ficticio',nivel='N0',erro=None,resposta={})
    result={'testes':[dict(teste='png',tipo='funcional',status='aprovado'),
                      dict(teste='nome_repetido',tipo='integridade',status='reprovado'),
                      dict(teste='mime',tipo='seguranca_conteudo',status='inconclusivo')]}
    row=coleta.summarize(record,result)
    assert row['funcional']=='aprovado' and row['contrato']['nome_repetido']=='reprovado'
    assert row['seguranca']=={'inconclusivo':1}


def test_plano_bloqueia_mudanca_de_fontes(tmp_path,monkeypatch):
    monkeypatch.setattr(coleta,'DATA',tmp_path)
    (tmp_path/'plano.json').write_text(json.dumps({'fontes_sha256':{'arquivo':'hash_original'},'imagem':'imagem'}))
    monkeypatch.setattr(coleta,'fingerprints',lambda:{'arquivo':'hash_alterado'})
    with pytest.raises(AssertionError,match='Fontes alteradas'):coleta.plan()
