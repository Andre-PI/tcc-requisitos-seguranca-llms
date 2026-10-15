"""Reproduz sete casos em matriz controlada; nao substitui resultados principais."""
import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from validar_aceitacao import BASE,execute,sha

IDS=(7,11,33,35,36,103,107)


def main():
    root=BASE/'execucoes'/('revisao-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    con=sqlite3.connect(BASE/'resultados.db');results=[]
    for variant in ('v1','v2'):
        python=BASE/f'.venv-revisao-{variant}'/'Scripts'/'python.exe'
        versions=json.loads(subprocess.check_output([str(python),'-c',"import json,sys,importlib.metadata as m;print(json.dumps(dict(python=sys.version,packages={d.metadata['Name'].lower():d.version for d in m.distributions()})))"],text=True))
        for gid in IDS:
            task,code=con.execute('SELECT tarefa,codigo FROM geracoes WHERE id=?',(gid,)).fetchone()
            folder=root/variant/f'g{gid}'
            r=execute(python,folder,code,task,15)
            r.update(geracao_id=gid,ambiente=versions,codigo_sha256=sha(code.encode()),variante=variant,
                     fontes={name:sha((BASE/name).read_bytes()) for name in ('aceitacao_worker.py','comportamento_worker.py','revisar_casos.py')})
            (folder/'resultado.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
            results.append(r)
            states=[x['status'] for x in r['testes'] if x['tipo']=='funcional_minimo']
            print(variant,gid,r['estado'],states,r.get('erro',''),flush=True)
    con.close()
    (root/'matriz.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(root)


if __name__=='__main__':main()
