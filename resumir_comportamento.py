"""Exporta a ultima verificacao de cada amostra para CSV e relatorio Markdown."""
import csv
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent


def main():
    con = sqlite3.connect(BASE/'resultados.db')
    rows = con.execute('''SELECT g.id,g.modelo,g.tarefa,g.nivel,v.estado,v.resultado_json,v.protocolo_sha256
      FROM geracoes g JOIN verificacoes_comportamentais v ON v.geracao_id=g.id
      WHERE v.id=(SELECT max(x.id) FROM verificacoes_comportamentais x WHERE x.geracao_id=g.id)
      ORDER BY g.modelo,g.tarefa,g.nivel,g.repeticao''').fetchall()
    con.close()
    dest=BASE/'docs'; dest.mkdir(exist_ok=True)
    groups=defaultdict(Counter); errors=[]; cases=[]; hashes=set()
    for gid,model,task,level,state,raw,phash in rows:
        r=json.loads(raw); hashes.add(phash)
        g=groups[model,task,level]; g['n']+=1
        g['execucao']+=state=='concluido'
        functional=[t for t in r['testes'] if t['tipo']=='funcional']
        g['funcional']+=bool(functional) and all(t['status']=='aprovado' for t in functional)
        detailed=[t for t in r['testes'] if t['tipo']=='contrato_N1']
        g['contrato']+=bool(detailed) and all(t['status']=='aprovado' for t in detailed)
        for t in r['testes']:
            cwe = 'CWE-307' if t['teste'] in ('limite_conta','limite_ip') else ('CWE-639' if t['teste'] in ('idor_A_acessa_B','idor_B_acessa_A') else '')
            cases.append(dict(geracao_id=gid,modelo=model,tarefa=task,nivel=level,teste=t['teste'],tipo=t['tipo'],cwe=cwe,status=t['status'],evidencia=json.dumps(t['evidencia'],ensure_ascii=False)))
            if t['teste'] in ('limite_conta','limite_ip','idor_A_acessa_B','idor_B_acessa_A'):
                g[t['teste']+'_'+t['status']]+=1
        if state!='concluido' or any(t['status']=='reprovado' for t in functional):
            errors.append(f"- g{gid} ({task}/{level}, {model}): {r.get('erro') or '; '.join(t['teste'] + ': ' + json.dumps(t['evidencia'],ensure_ascii=False) for t in functional if t['status']=='reprovado')}")
    with (dest/'casos-comportamentais.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['geracao_id','modelo','tarefa','nivel','teste','tipo','cwe','status','evidencia']);w.writeheader();w.writerows(cases)
    lines=['# Resultados comportamentais do piloto','',f'Amostras verificadas: {len(rows)}. Protocolos distintos na selecao mais recente: {len(hashes)}.', '',
           'Resultados exploratorios; aprovacao se refere somente aos casos implementados. Contrato N1 e medido separadamente porque nao e exigido no prompt N0. Falhas de seguranca de login indicam ausencia de bloqueio no limiar de 25 tentativas/60 segundos, nao ausencia universal de rate limit.', '',
           '| Modelo | Tarefa | Nivel | n | Execucao concluida | Funcional basico aprovado | Contrato N1 aprovado |',
           '|---|---|---|---:|---:|---:|---:|']
    for (m,t,n),g in groups.items():
        lines.append(f"| {m} | {t} | {n} | {g['n']} | {g['execucao']} | {g['funcional']} | {g['contrato']} |")
    lines+=['','## Seguranca por caso','','| Modelo | Tarefa | Nivel | Caso | Aprovado | Falha observada | Inconclusivo/nao executado |','|---|---|---|---|---:|---:|---:|']
    for (m,t,n),g in groups.items():
        for case in (('limite_conta','limite_ip') if t=='T01' else ('idor_A_acessa_B','idor_B_acessa_A')):
            ok=g[case+'_aprovado']; bad=g[case+'_vulneravel']
            lines.append(f"| {m} | {t} | {n} | {case} | {ok} | {bad} | {g['n']-ok-bad} |")
    lines+=['','## Falhas que exigem revisao','',*errors,'','## Limites de interpretacao','',
            'Em T06, a fixture substitui dependencias de autenticacao existentes para medir autorizacao entre duas identidades. O resultado nao atesta seguranca do autenticador original. Em N0, a propriedade e atribuida aos registros de teste; o acesso sem token e observado separadamente no CSV.', '',
            'Pydantic 2 pode rejeitar estruturas geradas para Pydantic 1. Isso e compatibilidade com o ambiente fixado, nao prova de que um requisito de seguranca causou falha funcional. Nao foi aplicado reparo automatico ao codigo gerado.', '',
            'Faltam testes de hash, logs, temporizacao, expiracao e outras propriedades. As adaptacoes e respostas individuais estao em execucoes/ e no SQLite. O protocolo completo esta em protocolo-comportamental.md.']
    (dest/'resultado-comportamental.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Relatorio: {dest / "resultado-comportamental.md"}')
    print(f'Amostras: {len(rows)}; protocolos: {len(hashes)}; casos: {len(cases)}')


if __name__=='__main__': main()
