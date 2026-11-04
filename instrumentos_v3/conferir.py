"""Confere os arquivos e resultados das validações v3 já registradas."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def conferir():
    antigos = novos = 0
    for tarefa in ('T03', 'T04', 'T07', 'T08', 'T09', 'T10'):
        report = json.loads((ROOT / f'docs/instrumentos-v3/{tarefa}-validacao-linux.json').read_text(encoding='utf-8'))
        for nome, sha in report['arquivos'].items():
            if hashlib.sha256((ROOT / nome).read_bytes()).hexdigest() != sha:
                raise ValueError('Fonte alterada depois da validação: ' + nome)
        assert len(report['probe']['confinamento']) >= 4 and all(report['probe']['confinamento'].values())
        for chave in ('referencias', 'regressao'):
            grupo = report[chave]
            assert grupo['referencias'] == grupo['expectativas_atendidas'] == len(grupo['resultados'])
            assert all(r['expectativa_atendida'] for r in grupo['resultados'])
            assert all('grupo_funcional' in t for r in grupo['resultados'] for t in r['testes'] if t['tipo'] == 'funcional')
        antigos += report['referencias']['referencias']
        novos += report['regressao']['referencias']
    print(f'Instrumentos v3: {antigos} referências anteriores e {novos} controles novos; hashes conferidos.')


if __name__ == '__main__':
    conferir()
