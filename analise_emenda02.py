"""Analise corrigida da Emenda 02: mesmo codigo registrado, com a reavaliacao v5 somente na T03."""
import json
from pathlib import Path
import analise_principal as a

DATA = a.DATA


def carregar():
    linhas = []
    for job in json.loads((DATA / 'plano.json').read_text(encoding='utf-8'))['jobs']:
        origem = DATA / 'reavaliacao-t03-v5' / f"{job['id']}.json" if job['tarefa'] == 'T03' else DATA / job['id'] / 'avaliacao.json'
        resultado = json.loads(origem.read_text(encoding='utf-8'))
        completo, base = a.desfecho_funcional(resultado, job['nivel'])
        linhas.append(dict(id=job['id'], tarefa=job['tarefa'], modelo=job['modelo'], nivel=job['nivel'],
                           seguranca=a.desfecho_seguranca(job['tarefa'], resultado), funcional=completo, funcional_base=base))
    return linhas


if __name__ == '__main__':
    (DATA / 'analise-emenda-02.json').write_bytes((json.dumps(a.analisar(carregar()), ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print('Analise corrigida gravada em', DATA / 'analise-emenda-02.json')
