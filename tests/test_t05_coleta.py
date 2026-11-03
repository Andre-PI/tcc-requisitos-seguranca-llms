from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import t05_coleta as coleta


def test_diagnostico_de_tokens_nao_vira_aprovacao_de_seguranca():
    record=dict(id='teste',modelo='ficticio',nivel='N0',erro=None,resposta={})
    result={'testes':[dict(teste='ciclo',tipo='funcional',status='aprovado'),dict(teste='token',tipo='diagnostico',status='sem_fraqueza_observada'),dict(teste='validade',tipo='seguranca',status='inconclusivo')]}
    row=coleta.summarize(record,result)
    assert row['funcional']=='aprovado' and row['seguranca']=={'inconclusivo':1}
    assert row['diagnostico']=={'token':'sem_fraqueza_observada'}


def test_impedimento_de_execucao_permanece_inconclusivo():
    record=dict(id='teste',modelo='ficticio',nivel='N3',erro=None,resposta={})
    row=coleta.summarize(record,{'erro':'ImportError','testes':[]})
    assert row['funcional']=='inconclusivo' and row['erro']=='ImportError' and not row['seguranca']
