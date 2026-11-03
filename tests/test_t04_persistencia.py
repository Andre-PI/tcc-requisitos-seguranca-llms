from pathlib import Path
import sys
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import t04_coleta


def test_gravacao_repete_so_operacao_de_arquivo_apos_bloqueio(tmp_path,monkeypatch):
    original=Path.replace
    attempts=[]
    def locked_once(path,target):
        attempts.append(1)
        if len(attempts)==1:raise PermissionError('arquivo em uso')
        return original(path,target)
    monkeypatch.setattr(Path,'replace',locked_once)
    monkeypatch.setattr(t04_coleta.time,'sleep',lambda seconds:None)
    t04_coleta.save(tmp_path/'resultado.json',{'resposta':'preservada'})
    assert json.loads((tmp_path/'resultado.json').read_text())=={'resposta':'preservada'}
    assert len(attempts)==2
