"""Indicadores da analise estatica previstos na subsecao 3.5, por modelo e nivel."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'dados' / 'coleta-principal'
ID = re.compile(r'(cp-\d{4})')


def achados():
    """Devolve os achados por ferramenta, com a geracao de origem."""
    b = json.loads((DATA / 'sast/bandit.json').read_text(encoding='utf-8'))
    s = json.loads((DATA / 'sast/semgrep.json').read_text(encoding='utf-8'))
    saida = [dict(ferramenta='bandit', id=ID.search(r['filename'].replace('\\', '/')).group(1), regra=r['test_id'], cwe=f"CWE-{r['issue_cwe']['id']}" if r.get('issue_cwe') else None, severidade=r['issue_severity']) for r in b['results']]
    for r in s['results']:
        cwe = (r['extra'].get('metadata') or {}).get('cwe')
        cwe = cwe[0] if isinstance(cwe, list) and cwe else cwe
        saida.append(dict(ferramenta='semgrep', id=ID.search(r['path'].replace('\\', '/')).group(1), regra=r['check_id'].split('.')[-1], cwe=(cwe or '').split(':')[0] or None, severidade=r['extra'].get('severity')))
    return saida, len(b.get('errors', [])), len(s['errors'])


def resumir():
    jobs = json.loads((DATA / 'plano.json').read_text(encoding='utf-8'))['jobs']
    analisadas = {j['id']: j for j in jobs if (DATA / j['id'] / 'amostra.py').exists()}
    lista, erros_b, erros_s = achados()
    tabela = {}
    for ferramenta in ('bandit', 'semgrep'):
        tabela[ferramenta] = {}
        dessa = [a for a in lista if a['ferramenta'] == ferramenta]
        for modelo in sorted({j['modelo'] for j in jobs}):
            for nivel in ('N0', 'N1', 'N2', 'N3'):
                ids = {i for i, j in analisadas.items() if j['modelo'] == modelo and j['nivel'] == nivel}
                daqui = [a for a in dessa if a['id'] in ids]
                tabela[ferramenta][f'{modelo}|{nivel}'] = dict(n=len(ids), com_achado=len({a['id'] for a in daqui}), achados=len(daqui))
        tabela[ferramenta + '_regras'] = Counter(a['regra'] for a in dessa).most_common(15)
        tabela[ferramenta + '_cwe'] = Counter(a['cwe'] or 'sem CWE' for a in dessa).most_common(15)
    return dict(respostas_com_codigo=len(analisadas), erros=dict(bandit=erros_b, semgrep=erros_s), **tabela)


if __name__ == '__main__':
    (DATA / 'sast/resumo.json').write_bytes((json.dumps(resumir(), ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print('Resumo gravado em', DATA / 'sast/resumo.json')
