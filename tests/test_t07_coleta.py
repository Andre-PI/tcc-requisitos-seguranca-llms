from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import t07_coleta as coleta


def test_injecao_de_argumentos_nao_e_somada_a_comandos():
    record=dict(id='teste',modelo='ficticio',nivel='N0',erro=None,resposta={})
    r=coleta.summarize(record,{'testes':[dict(teste='legitimo',tipo='funcional',status='aprovado'),dict(teste='shell',tipo='seguranca_comando',status='aprovado'),dict(teste='opcao',tipo='argumentos',status='reprovado')]})
    assert r['funcional']=='aprovado' and r['comandos']=={'aprovado':1} and r['argumentos']=={'reprovado':1}


def test_falha_sem_resultados_nao_aprova_seguranca():
    record=dict(id='teste',modelo='ficticio',nivel='N3',erro=None,resposta={})
    r=coleta.summarize(record,{'erro':'ImportError','testes':[]})
    assert r['funcional']=='inconclusivo' and not r['comandos'] and not r['argumentos'] and r['erro']=='ImportError'
