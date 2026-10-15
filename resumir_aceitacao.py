"""Relatorio por geracao; mantem falhas e falta de execucao no denominador."""
import csv
import json
import sqlite3
from collections import Counter,defaultdict
from pathlib import Path

BASE=Path(__file__).resolve().parent


def status_group(result,group):
    cases=[t for t in result['testes'] if t['tipo']==group]
    if result['estado']!='concluido' or not cases:return 'sem_execucao'
    return 'aprovado' if all(t['status']=='aprovado' for t in cases) else 'reprovado'


def main():
    con=sqlite3.connect(BASE/'resultados.db')
    rows=con.execute('''SELECT g.id,g.modelo,g.tarefa,g.nivel,g.repeticao,a.resultado_json,a.protocolo_sha256,a.artefatos
      FROM geracoes g JOIN aceitacoes a ON a.geracao_id=g.id
      WHERE a.id=(SELECT max(x.id) FROM aceitacoes x WHERE x.geracao_id=g.id)
      ORDER BY g.modelo,g.tarefa,g.nivel,g.repeticao''').fetchall()
    con.close()
    groups=defaultdict(Counter);samples=[];cases=[];errors=[];protocols=set()
    for gid,model,task,level,rep,raw,phash,artifacts in rows:
        r=json.loads(raw);protocols.add(phash)
        states={name:status_group(r,name) for name in ('funcional_minimo','contrato_N1','robustez')}
        group=groups[model,task,level];group['n']+=1
        for name,state in states.items():group[name+'_'+state]+=1
        samples.append(dict(geracao_id=gid,modelo=model,tarefa=task,nivel=level,repeticao=rep,**states,estado=r['estado'],erro=r.get('erro',''),protocolo_sha256=phash,artefatos=artifacts))
        for t in r['testes']:
            cases.append(dict(geracao_id=gid,modelo=model,tarefa=task,nivel=level,teste=t['teste'],grupo=t['tipo'],status=t['status'],evidencia=json.dumps(t['evidencia'],ensure_ascii=False)))
        if r['estado']!='concluido':errors.append(f"- g{gid} ({task}/{level}): {r.get('erro','sem diagnostico')}")
        else:
            diagnostics=list(dict.fromkeys(t['evidencia'].get('diagnostico','') for t in r['testes'] if t['status']=='reprovado' and isinstance(t['evidencia'],dict)))
            for message in diagnostics:
                if message:errors.append(f'- g{gid} ({task}/{level}): {message.splitlines()[0]}')
    for name,data in [('aceitacao-por-geracao.csv',samples),('aceitacao-por-caso.csv',cases)]:
        with (BASE/'docs'/name).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    lines=['# Aceitação funcional das três tarefas do piloto','',f'{len(samples)} gerações; {len(cases)} casos com resultado; {len(protocols)} protocolo(s) na seleção mais recente.', '',
           'Esta bateria foi definida após a coleta do piloto. Os critérios estão em criterios-aceitacao.json. Não é um pré-registro da coleta realizada. Nenhum código original foi reparado. Os resultados principais usam a stack já fixada no projeto; as comparações com Pydantic 1 ficam separadas.', '',
           'A tabela conta gerações aprovadas em todos os casos de cada grupo, e não porcentagem de casos individuais. Toda geração permanece no denominador n. Sem execução inclui timeout, erro de importação e ausência de adaptação permitida. O grupo funcional mínimo mede capacidades operacionais selecionadas; o contrato N1 mede as exigências detalhadas comuns a N1/N2/N3. A coluna N1 em N0 é uma referência de capacidade, não descumprimento de um requisito solicitado.', '',
           '| Modelo | Tarefa | Nível | n | Mínimo aprovado | Mínimo reprovado | Contrato N1 aprovado | Contrato N1 reprovado | Sem execução |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for (m,t,n),g in groups.items():
        lines.append(f"| {m} | {t} | {n} | {g['n']} | {g['funcional_minimo_aprovado']} | {g['funcional_minimo_reprovado']} | {g['contrato_N1_aprovado']} | {g['contrato_N1_reprovado']} | {g['funcional_minimo_sem_execucao']} |")
    lines+=['','## Impedimentos e diagnósticos','',*errors,'','## Uso dos resultados','',
            'Cruzar aceitacao-por-geracao.csv com os resultados comportamentais por geracao_id. Em T01, bloqueio por conta e IP não esgota a segurança do login; em T06, as identidades fornecidas pela fixture não validam o autenticador original. Em T02, aprovação funcional não prova ausência de SQL injection. Não combinar ausência de achados SAST com aprovação funcional para declarar uma amostra segura.', '',
            'As diferenças entre níveis são descritivas nesta etapa. A revisão encontrou incompatibilidades de bibliotecas, inclusive código de SQLAlchemy anterior à API 2.x. A stack não havia sido especificada nos prompts do piloto; portanto esses dados não sustentam uma alegação causal de perda funcional por requisitos de segurança.', '',
            'Antes da coleta definitiva, congelar versões e política de adaptação, incorporar as convenções funcionais igualmente nos prompts detalhados e verificar que as demais sete tarefas têm testes e fixtures equivalentes. Preservar este piloto separado da coleta principal.']
    (BASE/'docs'/'resultado-aceitacao.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'{len(samples)} geracoes; {len(cases)} casos; {len(protocols)} protocolos')
    for task in ('T01','T02','T06'):
        print(task,{group:dict(Counter(s[group] for s in samples if s['tarefa']==task)) for group in ('funcional_minimo','contrato_N1','robustez')})


if __name__=='__main__':main()
