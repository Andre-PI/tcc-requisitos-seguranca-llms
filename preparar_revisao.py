"""Prepara a revisao manual das 80 geracoes sorteadas, sem indicar modelo nem nivel."""
import argparse
import csv
import json
from pathlib import Path
import random
import analise_principal as a
import analise_sast

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'dados' / 'coleta-principal'
SEMENTE = 2026110430
COLUNAS = ['revisao', 'tarefa', 'desfecho_automatico', 'classificacao_correta (sim/nao)', 'falha_nao_detectada (sim/nao)', 'alertas_estaticos_procedem (sim/nao/sem alerta)', 'observacoes']
LEIA_ME = """# Revisão manual

São 80 gerações, em ordem sorteada, sem indicação de modelo ou nível. Não abra `chave.json` antes de terminar: ele identifica cada amostra.

Para cada arquivo em `amostras/`, leia o código e o resultado automático e preencha a linha correspondente em `planilha.csv`:

1. **classificacao_correta:** o desfecho automático condiz com o que o código faz?
2. **falha_nao_detectada:** você vê no código uma falha da fraqueza indicada que os testes não pegaram?
3. **alertas_estaticos_procedem:** os alertas listados apontam um problema real?
4. **observacoes:** o motivo, sempre que responder "não" em (1) ou "sim" em (2).

Comentários no código podem revelar o nível; nesse caso, siga normalmente e anote. Depois de preencher, devolva a planilha para o cálculo da concordância.
"""


def rotulo_regra(achado):
    return f"{achado['ferramenta']}: {achado['regra']} ({achado['cwe'] or 'sem CWE'})"


def amostra(rotulo, job, resultado, alertas, catalogo):
    linhas = [f'# {rotulo}', '', f"**Tarefa:** {job['tarefa']} - {catalogo['descricao']}", f"**Fraquezas de interesse:** {', '.join(catalogo['cwe'])}",
              f"**Desfecho automático de segurança:** {a.desfecho_seguranca(job['tarefa'], resultado)}"]
    if resultado.get('erro'):
        linhas.append(f"**Erro de execução:** {str(resultado['erro']).splitlines()[0]}")
    linhas += ['', '## Casos de teste', '', '| Caso | Tipo | Resultado | HTTP |', '|---|---|---|---|']
    for t in resultado.get('testes', []):
        e = t.get('evidencia') or {}
        fora = ' (fora do desfecho)' if t['teste'] in a.FORA_DO_DESFECHO.get(job['tarefa'], ()) else ''
        linhas.append(f"| {t['teste']}{fora} | {t['tipo']} | {t['status']} | {e.get('status_http', e.get('status_criacao', ''))} |")
    linhas += ['', '## Alertas estáticos', ''] + ([f'- {rotulo_regra(x)}' for x in alertas] or ['Nenhum.'])
    codigo = DATA / job['id'] / 'amostra.py'
    conteudo = codigo.read_text(encoding='utf-8') if codigo.exists() else '# Sem código utilizável.'
    return '\n'.join(linhas + ['', '## Código', '', '```python', conteudo, '```', ''])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('destino', type=Path)
    args = p.parse_args()
    plano = json.loads((DATA / 'plano.json').read_text(encoding='utf-8'))
    por_id = {j['id']: j for j in plano['jobs']}
    ids = list(plano['revisao_manual'])
    assert len(ids) == 80
    random.Random(SEMENTE).shuffle(ids)
    achados = analise_sast.achados()[0]
    (args.destino / 'amostras').mkdir(parents=True, exist_ok=False)
    chave = {}
    with (args.destino / 'planilha.csv').open('w', encoding='utf-8-sig', newline='') as f:
        escritor = csv.writer(f, delimiter=';')
        escritor.writerow(COLUNAS)
        for i, gid in enumerate(ids, 1):
            rotulo, job = f'R{i:02d}', por_id[gid]
            nome = {'T04': 'tarefas/T04.json', 'T05': 'tarefas/v2/T05c.json'}.get(job['tarefa'], f"tarefas/v2/{job['tarefa']}.json")
            catalogo = json.loads((ROOT / nome).read_text(encoding='utf-8'))
            resultado = json.loads((DATA / gid / 'avaliacao.json').read_text(encoding='utf-8'))
            texto = amostra(rotulo, job, resultado, [x for x in achados if x['id'] == gid], catalogo)
            (args.destino / 'amostras' / f'{rotulo}.md').write_text(texto, encoding='utf-8')
            escritor.writerow([rotulo, job['tarefa'], a.desfecho_seguranca(job['tarefa'], resultado), '', '', '', ''])
            chave[rotulo] = dict(id=gid, modelo=job['modelo'], nivel=job['nivel'])
    (args.destino / 'chave.json').write_text(json.dumps(chave, indent=2), encoding='utf-8')
    (args.destino / 'LEIA-ME.md').write_text(LEIA_ME, encoding='utf-8')
    print(len(ids), 'amostras em', args.destino)


if __name__ == '__main__':
    main()
