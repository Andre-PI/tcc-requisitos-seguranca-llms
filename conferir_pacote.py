"""Confere o pacote sem rede e sem executar código gerado."""
from pathlib import Path
import hashlib,json,sqlite3
from collections import Counter

ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'manifesto-pacote.json').read_text(encoding='utf-8'))
for item in manifest['arquivos']:
    p=ROOT/item['caminho']
    assert p.is_file(), f"Arquivo ausente: {item['caminho']}"
    assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'], f"Arquivo alterado: {item['caminho']}"
c=sqlite3.connect((ROOT/'resultados.db').as_uri()+'?mode=ro',uri=True)
assert c.execute('pragma integrity_check').fetchone()[0]=='ok'
rows=c.execute('select id,codigo from geracoes where erro is null').fetchall()
assert len(rows)==72
for gid,code in rows:
    assert (ROOT/'codigos'/f'g{gid}.py').read_text(encoding='utf-8')==code,f'Codigo divergente: g{gid}'
assert c.execute('select count(*) from analisadas').fetchone()[0]==72
assert c.execute('select count(*) from achados').fetchone()[0]==4
totals=Counter();cases=0
for table,expected in [('aceitacoes',72),('verificacoes_comportamentais',48)]:
    results=c.execute(f"select geracao_id,codigo_sha256,resultado_json,artefatos from {table} t where t.id=(select max(x.id) from {table} x where x.geracao_id=t.geracao_id)").fetchall()
    assert len(results)==expected
    for gid,sha,raw,folder in results:
        code=c.execute('select codigo from geracoes where id=?',(gid,)).fetchone()[0]
        assert hashlib.sha256(code.encode()).hexdigest()==sha
        local=ROOT/Path(folder.replace('\\','/'))
        assert local.is_dir(),f'Artefato ausente: {folder}'
        r=json.loads(raw)
        if table=='aceitacoes':
            cases+=len(r['testes'])
            tests=[t for t in r['testes'] if t['tipo']=='funcional_minimo']
            status='sem_execucao' if r['estado']!='concluido' or not tests else 'aprovado' if all(t['status']=='aprovado' for t in tests) else 'reprovado'
            totals[status]+=1
assert totals=={'aprovado':57,'reprovado':9,'sem_execucao':6}
assert cases==1797
print('Integridade e hashes conferidos. 72 geracoes; 72 analises estaticas; 4 alertas.')
print('Aceitacao minima:',dict(totals),'| casos:',cases,'| comportamentais: 48')
print('Esta conferencia nao reexecuta os testes nem certifica autenticidade da coleta.')
