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

t04=ROOT/'dados'/'t04-exploratoria'
if (t04/'resumo.json').exists():
    plan=json.loads((t04/'plano.json').read_text(encoding='utf-8'))
    assert len(plan['jobs'])==8
    expected=plan['fontes_sha256']
    if (t04/'emendas.json').exists():
        for change in json.loads((t04/'emendas.json').read_text(encoding='utf-8')):
            assert change['fontes_anteriores']==expected
            expected=change['fontes_atuais']
    for name,sha in expected.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    original=t04/'fontes-originais'/'t04_coleta.py'
    if original.exists():
        assert hashlib.sha256(original.read_bytes()).hexdigest()==plan['fontes_sha256']['t04_coleta.py']
    calls=0;ids=set()
    for job in plan['jobs']:
        folder=t04/job['id']
        generation=json.loads((folder/'geracao.json').read_text(encoding='utf-8'))
        assert generation['concluida_em']
        assert generation['prompt']==job['prompt']
        assert generation['payload']['model']==job['modelo']
        assert all(generation['payload'][k]==v for k,v in plan['parametros'].items())
        calls+=len(generation['tentativas'])
        if generation['erro'] is None:
            assert hashlib.sha256((folder/'amostra.py').read_bytes()).hexdigest()==generation['codigo_sha256']
            ids.add(generation['resposta']['id'])
        evaluation=json.loads((folder/'avaliacao.json').read_text(encoding='utf-8'))
        assert evaluation.get('imagem',plan['imagem'])==plan['imagem']
    assert len(ids)==8 and calls==8
    print('T04 exploratoria: 8 geracoes, 8 requisicoes; prompts, parametros, imagem e hashes conferidos separadamente do piloto.')

# Validacao T03 de instrumentos: nao acrescenta geracoes ao piloto.
t03_report=ROOT/'docs'/'T03-validacao-linux.json'
if t03_report.exists():
    report=json.loads(t03_report.read_text(encoding='utf-8'))
    assert report['referencias']==9 and report['expectativas_atendidas']==9 and report['container_exit']==0
    assert all(r['expectativa_atendida'] and r['link_disponivel'] and len(r['testes'])==18 for r in report['resultados'])
    for name,sha in report['arquivos'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    print('T03: 9 referencias e 18 casos por referencia; hashes dos instrumentos conferidos.')

t03=ROOT/'dados'/'t03-exploratoria'
if (t03/'resumo.json').exists():
    plan=json.loads((t03/'plano.json').read_text(encoding='utf-8'))
    assert len(plan['jobs'])==8
    for name,sha in plan['fontes_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    calls=0;ids=set()
    for job in plan['jobs']:
        folder=t03/job['id'];g=json.loads((folder/'geracao.json').read_text(encoding='utf-8'))
        assert plan['registrado_em']<=g['iniciado_em']<=g['concluida_em']
        assert g['prompt']==job['prompt'] and g['payload']['messages']==[{'role':'user','content':job['prompt']}]
        assert g['payload']['model']==job['modelo']
        assert all(g['payload'][k]==v for k,v in plan['parametros'].items())
        calls+=len(g['tentativas'])
        if g['resposta']:ids.add(g['resposta']['id'])
        if 'codigo_sha256' in g:
            assert hashlib.sha256((folder/'amostra.py').read_bytes()).hexdigest()==g['codigo_sha256']
        result=json.loads((folder/'avaliacao.json').read_text(encoding='utf-8'))
        if 'imagem' in result:assert result['imagem']==plan['imagem']
    assert len(ids)==8 and calls==8
    print('T03 exploratoria: 8 respostas em 8 requisicoes; plano anterior as chamadas, prompts, parametros, fontes e imagem conferidos.')

t05_report=ROOT/'docs'/'T05-validacao-linux.json'
if t05_report.exists():
    report=json.loads(t05_report.read_text(encoding='utf-8'))
    assert report['referencias']==report['expectativas_atendidas']==11 and report['container_exit']==0
    assert len(report['probe']['confinamento'])==4 and all(report['probe']['confinamento'].values())
    assert all(r['expectativa_atendida'] and len(r['testes'])==12 for r in report['resultados'])
    for name,sha in report['arquivos'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    print('T05: 11 referencias, 12 cenarios por referencia; isolamento e hashes dos instrumentos conferidos.')

t05=ROOT/'dados/t05-exploratoria'
if (t05/'resumo.json').exists():
    plan=json.loads((t05/'plano.json').read_text(encoding='utf-8'))
    assert len(plan['jobs'])==8
    for name,sha in plan['fontes_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    calls=0;ids=set();end_times=[]
    for job in plan['jobs']:
        folder=t05/job['id'];g=json.loads((folder/'geracao.json').read_text(encoding='utf-8'))
        assert plan['registrado_em']<=g['iniciado_em']<=g['concluida_em']
        assert g['prompt']==job['prompt'] and g['payload']['messages']==[{'role':'user','content':job['prompt']}]
        assert g['payload']['model']==job['modelo']
        assert all(g['payload'][k]==v for k,v in plan['parametros'].items())
        assert hashlib.sha256((folder/'amostra.py').read_bytes()).hexdigest()==g['codigo_sha256']
        calls+=len(g['tentativas']);ids.add(g['resposta']['id']);end_times.append(g['concluida_em'])
        result=json.loads((folder/'avaliacao.json').read_text(encoding='utf-8'))
        assert result['imagem']==plan['imagem']
    assert len(ids)==8 and calls==8
    for diagnostic in ['t05-sensibilidade','t05-sensibilidade-v2']:
        folder=ROOT/'dados'/diagnostic
        dp=json.loads((folder/'plano.json').read_text(encoding='utf-8'))
        assert dp['registrado_em']>=max(end_times) and dp['imagem_original']==plan['imagem']
        for name,sha in dp['fontes_sha256'].items():
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
        summary=json.loads((folder/'resumo.json').read_text(encoding='utf-8'))
        assert summary['novas_chamadas_api']==0 and len(summary['amostras'])==16
        for condition in dp['condicoes']:
            for job in plan['jobs']:
                result=json.loads((folder/condition/job['id']/'avaliacao.json').read_text(encoding='utf-8'))
                assert result['imagem']==dp['imagem']
    review=json.loads((ROOT/'docs/T05-revisao-tokens.json').read_text(encoding='utf-8'))
    assert len(review['observacoes'])==8 and review['revisao_humana_independente']=='pendente'
    for row in review['observacoes']:
        code=(t05/row['id']/'amostra.py').read_bytes()
        assert hashlib.sha256(code).hexdigest()==row['codigo_sha256']
        lines=code.decode('utf-8').splitlines()
        for evidence in row['evidencias'].values():assert lines[evidence['linha']-1].strip()==evidence['trecho']
    print('T05 exploratoria: 8 respostas em 8 chamadas; diagnosticos separados, fontes e revisao por linha conferidos.')

t07_report=ROOT/'docs/T07-validacao-linux.json'
if t07_report.exists():
    report=json.loads(t07_report.read_text(encoding='utf-8'))
    assert report['referencias']==report['expectativas_atendidas']==10 and report['container_exit']==0
    assert len(report['probe']['confinamento'])==4 and all(report['probe']['confinamento'].values())
    assert all(r['expectativa_atendida'] and len(r['testes'])==15 for r in report['resultados'])
    for name,sha in report['arquivos'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    print('T07: 10 referencias, 15 cenarios por referencia; hashes e isolamento dos instrumentos conferidos.')

t07=ROOT/'dados/t07-exploratoria'
if (t07/'resumo.json').exists():
    plan=json.loads((t07/'plano.json').read_text(encoding='utf-8'))
    assert len(plan['jobs'])==8
    for name,sha in plan['fontes_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    calls=0;ids=set()
    for job in plan['jobs']:
        folder=t07/job['id'];g=json.loads((folder/'geracao.json').read_text(encoding='utf-8'))
        assert plan['registrado_em']<=g['iniciado_em']<=g['concluida_em']
        assert g['prompt']==job['prompt'] and g['payload']['messages']==[{'role':'user','content':job['prompt']}]
        assert g['payload']['model']==job['modelo']
        assert all(g['payload'][k]==v for k,v in plan['parametros'].items())
        assert hashlib.sha256((folder/'amostra.py').read_bytes()).hexdigest()==g['codigo_sha256']
        calls+=len(g['tentativas']);ids.add(g['resposta']['id'])
        result=json.loads((folder/'avaliacao.json').read_text(encoding='utf-8'))
        assert result['imagem']==plan['imagem']
    assert calls==len(ids)==8
    review=json.loads((ROOT/'docs/T07-revisao-processos.json').read_text(encoding='utf-8'))
    assert len(review['observacoes'])==8
    for row in review['observacoes']:
        code=(t07/row['id']/'amostra.py').read_bytes()
        assert hashlib.sha256(code).hexdigest()==row['codigo_sha256']
        assert row['revisao_humana_independente']=='pendente'
        lines=code.decode('utf-8').splitlines()
        for point in row['evidencias'].values():assert lines[point['linha']-1].strip()==point['trecho']
    print('T07 exploratoria: 8 respostas em 8 chamadas; plano, fontes, imagem e evidencias da revisao conferidos.')

t07v2=ROOT/'dados/t07-exploratoria-v2'
if (t07v2/'resumo.json').exists():
    plan=json.loads((t07v2/'plano.json').read_text(encoding='utf-8'))
    assert len(plan['jobs'])==8
    for name,sha in plan['fontes_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    calls=0;ids=set()
    for job in plan['jobs']:
        assert ' -- ' not in job['prompt'] or job['nivel']=='N3'
        folder=t07v2/job['id'];g=json.loads((folder/'geracao.json').read_text(encoding='utf-8'))
        assert plan['registrado_em']<=g['iniciado_em']<=g['concluida_em']
        assert g['prompt']==job['prompt'] and g['payload']['messages']==[{'role':'user','content':job['prompt']}]
        assert g['payload']['model']==job['modelo']
        assert all(g['payload'][k]==v for k,v in plan['parametros'].items())
        assert hashlib.sha256((folder/'amostra.py').read_bytes()).hexdigest()==g['codigo_sha256']
        calls+=len(g['tentativas']);ids.add(g['resposta']['id'])
        result=json.loads((folder/'avaliacao.json').read_text(encoding='utf-8'))
        assert result['imagem']==plan['imagem']
    assert calls==len(ids)==8
    print('T07 exploratoria v2: 8 respostas em 8 chamadas; plano, fontes, imagem e prompts conferidos.')

for folder_name,total_refs,report_name in [('t03-exploratoria-v2',9,'T03'),('t08-exploratoria-v2',11,'T08'),('t05b-exploratoria-v2',11,'T05b'),('t05c-exploratoria-v2',11,'T05c'),('t09-exploratoria-v2',12,'T09'),('t10-exploratoria-v2',12,'T10'),('t01-exploratoria-v2',11,'T01'),('t02-exploratoria-v2',11,'T02'),('t06-exploratoria-v2',10,'T06')]:
    base=ROOT/'dados'/folder_name
    if not (base/'resumo.json').exists():continue
    plan=json.loads((base/'plano.json').read_text(encoding='utf-8'))
    assert len(plan['jobs'])==8
    for name,sha in plan['fontes_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    report=json.loads((ROOT/f'docs/{report_name}-validacao-linux.json').read_text(encoding='utf-8'))
    assert report['referencias']==report['expectativas_atendidas']==total_refs and report['imagem']==plan['imagem']
    calls=0;ids=set()
    for job in plan['jobs']:
        folder=base/job['id'];g=json.loads((folder/'geracao.json').read_text(encoding='utf-8'))
        assert plan['registrado_em']<=g['iniciado_em']<=g['concluida_em']
        assert g['prompt']==job['prompt'] and g['payload']['messages']==[{'role':'user','content':job['prompt']}]
        assert g['payload']['model']==job['modelo']
        assert all(g['payload'][k]==v for k,v in plan['parametros'].items())
        if g.get('codigo_sha256'):assert hashlib.sha256((folder/'amostra.py').read_bytes()).hexdigest()==g['codigo_sha256']
        else:assert g['erro'] and not (folder/'amostra.py').exists()
        calls+=len(g['tentativas']);ids.add(g['resposta']['id'])
        result=json.loads((folder/'avaliacao.json').read_text(encoding='utf-8'))
        if not g['erro']:assert result['imagem']==plan['imagem']
    assert calls==len(ids)==8
    print(folder_name+': 8 respostas em 8 chamadas; plano, fontes, imagem e validacao conferidos.')

t08_report=ROOT/'docs/T08-validacao-linux.json'
if t08_report.exists():
    report=json.loads(t08_report.read_text(encoding='utf-8'))
    assert report['referencias']==report['expectativas_atendidas']==11 and report['container_exit']==0
    assert len(report['probe']['confinamento'])==4 and all(report['probe']['confinamento'].values())
    assert all(r['expectativa_atendida'] and len(r['testes'])==24 for r in report['resultados'])
    for name,sha in report['arquivos'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    print('T08: 11 referencias, 24 cenarios por referencia; hashes e isolamento registrados.')
