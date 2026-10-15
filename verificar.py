"""Verificacao comportamental T01/T06, preservando codigo e evidencia por amostra."""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
VERSION = "piloto-comportamental-v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def connect(path):
    if not path.is_file():
        raise SystemExit(f"Banco nao encontrado: {path}")
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE IF NOT EXISTS verificacoes_comportamentais (
      id INTEGER PRIMARY KEY, geracao_id INTEGER NOT NULL,
      codigo_sha256 TEXT NOT NULL, protocolo_sha256 TEXT NOT NULL,
      estado TEXT NOT NULL, resultado_json TEXT NOT NULL,
      artefatos TEXT NOT NULL, criado_em TEXT NOT NULL,
      UNIQUE(geracao_id,codigo_sha256,protocolo_sha256))""")
    con.commit()
    return con


def resumo(con):
    rows = con.execute("""SELECT g.modelo,g.nivel,g.tarefa,v.resultado_json
      FROM verificacoes_comportamentais v JOIN geracoes g ON g.id=v.geracao_id
      WHERE v.id=(SELECT max(v2.id) FROM verificacoes_comportamentais v2 WHERE v2.geracao_id=g.id)
      ORDER BY g.modelo,g.tarefa,g.nivel""").fetchall()
    groups = {}
    for model, level, task, raw in rows:
        group = groups.setdefault((model, task, level), dict(n=0, funcional_ok=0, seguranca_com_falha=0, inconclusivo=0))
        group['n'] += 1
        r = json.loads(raw)
        functional = [t for t in r['testes'] if t['tipo'] == 'funcional']
        group['funcional_ok'] += bool(functional) and all(t['status']=='aprovado' for t in functional)
        group['seguranca_com_falha'] += any(t['tipo']=='seguranca' and t['status']=='vulneravel' for t in r['testes'])
        group['inconclusivo'] += r['estado']!='concluido' or any(t['status']=='inconclusivo' for t in r['testes'])
    for key, value in groups.items():
        print(*key, json.dumps(value, ensure_ascii=False))
    print('Categorias podem se sobrepor; funcional_ok cobre somente os casos implementados.')
    return [{"modelo":k[0], "tarefa":k[1], "nivel":k[2], **v} for k,v in groups.items()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--banco', type=Path, default=BASE/'resultados.db')
    p.add_argument('--tarefa', choices=('T01','T06'))
    p.add_argument('--ids', type=int, nargs='+')
    p.add_argument('--resumo', action='store_true')
    p.add_argument('--tentativas', type=int, default=25)
    p.add_argument('--timeout', type=int, default=150)
    args = p.parse_args()
    if not 1 <= args.tentativas <= 25 or args.timeout < 1:
        p.error('tentativas: 1 a 25; timeout deve ser positivo')
    con = connect(args.banco)
    if args.resumo:
        resumo(con); con.close(); return
    worker = BASE/'comportamento_worker.py'
    packages = subprocess.check_output([sys.executable,'-m','pip','freeze'], text=True)
    protocol = dict(versao=VERSION, tentativas=args.tentativas, janela_maxima=60,
                    timeout=args.timeout, python=sys.version, dependencias=packages,
                    worker_sha256=digest(worker.read_bytes()), runner_sha256=digest(Path(__file__).read_bytes()))
    phash = digest(json.dumps(protocol, sort_keys=True).encode())
    rows = con.execute("SELECT id,tarefa,codigo FROM geracoes WHERE erro IS NULL AND tarefa IN ('T01','T06') ORDER BY id").fetchall()
    root = BASE/'execucoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    count = 0
    for gid, task, code in rows:
        if args.tarefa and task!=args.tarefa or args.ids and gid not in args.ids:
            continue
        sha = digest(code.encode())
        if con.execute('SELECT 1 FROM verificacoes_comportamentais WHERE geracao_id=? AND codigo_sha256=? AND protocolo_sha256=?',(gid,sha,phash)).fetchone():
            print(f'[pulado] g{gid}', flush=True); continue
        folder = root/f'g{gid}'; folder.mkdir(parents=True)
        source = folder/'amostra.py'; source.write_text(code, encoding='utf-8')
        output = folder/'resultado.json'
        # Nao repassar chave da API, variaveis de banco ou parametros do usuario.
        allowed = {'SYSTEMROOT','WINDIR','TEMP','TMP','PATH','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE'}
        env = {k:v for k,v in os.environ.items() if k.upper() in allowed}
        env.update(PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
        try:
            proc = subprocess.run([sys.executable, str(worker), str(source), task, str(output), str(args.tentativas)],
                                  cwd=folder, env=env, capture_output=True, timeout=args.timeout)
            (folder/'stdout.txt').write_bytes(proc.stdout)
            (folder/'stderr.txt').write_bytes(proc.stderr)
            if proc.returncode or not output.exists():
                raise RuntimeError(f'Worker encerrou com codigo {proc.returncode}; consultar stderr')
            result = json.loads(output.read_text(encoding='utf-8'))
        except (subprocess.TimeoutExpired, RuntimeError) as exc:
            result = dict(estado='inconclusivo', erro=str(exc), adaptacoes=[], testes=[dict(teste='execucao',tipo='infraestrutura',status='inconclusivo',evidencia=str(exc))])
        result.update(geracao_id=gid, codigo_sha256=sha, protocolo=protocol)
        raw = json.dumps(result, ensure_ascii=False, indent=2)
        output.write_text(raw, encoding='utf-8')
        if digest(source.read_text(encoding='utf-8').encode()) != sha:
            raise RuntimeError('Codigo original alterado durante execucao')
        con.execute('INSERT INTO verificacoes_comportamentais (geracao_id,codigo_sha256,protocolo_sha256,estado,resultado_json,artefatos,criado_em) VALUES (?,?,?,?,?,?,?)',
                    (gid,sha,phash,result['estado'],raw,str(folder.relative_to(BASE)),datetime.now(timezone.utc).isoformat()))
        con.commit(); count += 1
        print(f"[{result['estado']}] g{gid} {task} " + result.get('erro',''), flush=True)
    summary = resumo(con)
    if count:
        (root/'resumo.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
        (root/'protocolo.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'Artefatos: {root}')
    con.close()


if __name__ == '__main__':
    main()
