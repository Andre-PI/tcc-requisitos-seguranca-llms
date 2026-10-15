"""Executa a aceitacao das 72 amostras, com evidencias e retomada versionadas."""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path

BASE=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def clean_env():
    allowed={'SYSTEMROOT','WINDIR','TEMP','TMP','PATH','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
    return {**{k:v for k,v in os.environ.items() if k.upper() in allowed},'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'}


def execute(python,folder,code,task,timeout):
    folder.mkdir(parents=True)
    source=folder/'amostra.py';source.write_text(code,encoding='utf-8')
    output=folder/'resultado.json'
    try:
        p=subprocess.run([str(python),str(BASE/'aceitacao_worker.py'),str(source),task,str(output)],cwd=folder,env=clean_env(),capture_output=True,timeout=timeout)
        (folder/'stdout.txt').write_bytes(p.stdout);(folder/'stderr.txt').write_bytes(p.stderr)
        if p.returncode or not output.exists():raise RuntimeError(f'worker exit={p.returncode}; consultar stderr')
        result=json.loads(output.read_text(encoding='utf-8'))
    except subprocess.TimeoutExpired as exc:
        (folder/'stdout.txt').write_bytes(exc.stdout or b'');(folder/'stderr.txt').write_bytes(exc.stderr or b'')
        result=dict(estado='inconclusivo',erro=f'timeout de {timeout}s',categoria='timeout',testes=[],adaptacoes=[])
    except RuntimeError as exc:
        result=dict(estado='inconclusivo',erro=str(exc),categoria='worker',testes=[],adaptacoes=[])
    assert sha(source.read_text(encoding='utf-8').encode())==sha(code.encode())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ids',type=int,nargs='+')
    p.add_argument('--timeout',type=int,default=30)
    args=p.parse_args()
    if args.timeout<1:p.error('timeout deve ser positivo')
    protocol=dict(versao='aceitacao-piloto-1',python=sys.version,timeout=args.timeout,
                  dependencias=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),
                  arquivos={name:sha((BASE/name).read_bytes()) for name in ('aceitacao_worker.py','comportamento_worker.py','validar_aceitacao.py','docs/criterios-aceitacao.json')})
    phash=sha(json.dumps(protocol,sort_keys=True).encode())
    con=sqlite3.connect(BASE/'resultados.db')
    con.execute('''CREATE TABLE IF NOT EXISTS aceitacoes(
      id INTEGER PRIMARY KEY,geracao_id INTEGER NOT NULL,codigo_sha256 TEXT NOT NULL,protocolo_sha256 TEXT NOT NULL,
      estado TEXT NOT NULL,resultado_json TEXT NOT NULL,artefatos TEXT NOT NULL,criado_em TEXT NOT NULL,
      UNIQUE(geracao_id,codigo_sha256,protocolo_sha256))''');con.commit()
    root=BASE/'execucoes'/('aceitacao-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    for gid,task,code in con.execute("SELECT id,tarefa,codigo FROM geracoes WHERE erro IS NULL ORDER BY id").fetchall():
        if args.ids and gid not in args.ids:continue
        codehash=sha(code.encode())
        if con.execute('SELECT 1 FROM aceitacoes WHERE geracao_id=? AND codigo_sha256=? AND protocolo_sha256=?',(gid,codehash,phash)).fetchone():
            print(f'[pulado] g{gid}',flush=True);continue
        folder=root/f'g{gid}'
        r=execute(sys.executable,folder,code,task,args.timeout)
        r.update(geracao_id=gid,codigo_sha256=codehash,protocolo=protocol)
        raw=json.dumps(r,ensure_ascii=False,indent=2)
        (folder/'resultado.json').write_text(raw,encoding='utf-8')
        con.execute('INSERT INTO aceitacoes (geracao_id,codigo_sha256,protocolo_sha256,estado,resultado_json,artefatos,criado_em) VALUES (?,?,?,?,?,?,?)',
                    (gid,codehash,phash,r['estado'],raw,str(folder.relative_to(BASE)),datetime.now(timezone.utc).isoformat()));con.commit()
        failed=sum(t['status']!='aprovado' for t in r['testes'])
        print(f"[{r['estado']}] g{gid} {task}: {len(r['testes'])} casos, {failed} reprovados. {r.get('erro','')}",flush=True)
    con.close()


if __name__=='__main__':main()
