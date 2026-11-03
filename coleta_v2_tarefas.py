"""Executa coleta_v2 com a configuracao em tarefas/v2/coleta-Txx.json, sem alterar coleta_v2.py."""
import hashlib
import json
from pathlib import Path
import sys
import coleta_v2

ROOT = Path(__file__).resolve().parent


def configurar(tarefa):
    cfg = json.loads((ROOT / f'tarefas/v2/coleta-{tarefa}.json').read_text(encoding='utf-8'))
    cfg['fontes'] = cfg['fontes'] + ['coleta_v2_tarefas.py', f'tarefas/v2/coleta-{tarefa}.json']
    validacao = json.loads((ROOT / f'docs/{cfg.get("validacao", tarefa + "-validacao-linux")}.json').read_text(encoding='utf-8'))
    for nome, sha in validacao['arquivos'].items():
        assert hashlib.sha256((ROOT / nome).read_bytes()).hexdigest() == sha, 'Instrumento alterado depois da validacao: ' + nome
    coleta_v2.TAREFAS[tarefa] = cfg


if __name__ == '__main__':
    configurar(sys.argv[1])
    coleta_v2.main()
