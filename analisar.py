#!/usr/bin/env python3
"""
Analise estatica dos codigos gerados pelo piloto.py.

Le a tabela 'geracoes' do resultados.db, grava cada codigo em disco,
roda bandit e semgrep sobre o conjunto, mapeia os achados para CWE e
grava tudo na tabela 'achados'.

Uso:
    pip install bandit semgrep
    python analisar.py                 # analisa tudo que ainda nao foi analisado
    python analisar.py --refazer       # descarta a analise anterior e refaz
    python analisar.py --resumo        # so mostra a tabela de resultados

Observacao: na primeira execucao o semgrep baixa as regras da internet.
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
BANCO = str(BASE / "resultados.db")
RELATORIOS = BASE / "relatorios-sast" / datetime.now().strftime("%Y%m%d-%H%M%S")
PASTA = str(BASE / "codigos")          # onde os .py sao gravados, para inspecao manual
REGRAS_SEMGREP = "p/python"

# Bandit usa identificadores proprios (B105, B608...). O mapa abaixo cobre os
# testes relevantes para as tarefas do estudo. O que nao estiver aqui e
# gravado com cwe NULL e revisado manualmente.
BANDIT_CWE = {
    "B105": "CWE-259", "B106": "CWE-259", "B107": "CWE-259",
    "B303": "CWE-327", "B324": "CWE-327", "B305": "CWE-327",
    "B311": "CWE-330",
    "B301": "CWE-502", "B403": "CWE-502", "B506": "CWE-502",
    "B602": "CWE-78", "B603": "CWE-78", "B604": "CWE-78",
    "B605": "CWE-78", "B606": "CWE-78", "B607": "CWE-78",
    "B608": "CWE-89",
    "B201": "CWE-489", "B104": "CWE-605",
    "B310": "CWE-918", "B501": "CWE-295",
}

CWE_RE = re.compile(r"CWE-(\d+)")


def conectar():
    if not os.path.exists(BANCO):
        sys.exit(f"Nao encontrei {BANCO}. Rode o piloto.py antes.")
    con = sqlite3.connect(BANCO)
    con.execute("""
        CREATE TABLE IF NOT EXISTS achados (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            geracao_id  INTEGER NOT NULL REFERENCES geracoes(id),
            ferramenta  TEXT NOT NULL,
            regra       TEXT NOT NULL,
            cwe         TEXT,
            severidade  TEXT,
            linha       INTEGER,
            mensagem    TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS analisadas (
            geracao_id INTEGER PRIMARY KEY REFERENCES geracoes(id)
        )
    """)
    con.commit()
    return con


def exportar(con, refazer):
    """Grava os codigos ainda nao analisados em PASTA/g<id>.py."""
    if refazer:
        con.execute("DELETE FROM analisadas")
    os.makedirs(PASTA, exist_ok=True)
    # Cada execucao usa somente os arquivos selecionados, sem apagar exportacoes.

    linhas = con.execute("""
        SELECT g.id, g.codigo FROM geracoes g
        WHERE g.erro IS NULL AND g.codigo IS NOT NULL AND g.codigo <> ''
          AND g.id NOT IN (SELECT geracao_id FROM analisadas)
    """).fetchall()

    for gid, codigo in linhas:
        with open(os.path.join(PASTA, f"g{gid}.py"), "w", encoding="utf-8") as f:
            f.write(codigo)
    return [gid for gid, _ in linhas]


def id_do_arquivo(caminho):
    nome = os.path.basename(caminho)
    m = re.match(r"g(\d+)\.py$", nome)
    return int(m.group(1)) if m else None


def rodar(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        raise RuntimeError(f"Ferramenta indisponivel: {cmd[0]}: {e}") from e
    RELATORIOS.mkdir(parents=True, exist_ok=True)
    nome = "bandit" if "bandit" in cmd else "semgrep"
    (RELATORIOS / f"{nome}.json").write_text(p.stdout, encoding="utf-8")
    (RELATORIOS / f"{nome}.stderr.txt").write_text(p.stderr, encoding="utf-8")
    if p.returncode not in (0, 1):
        raise RuntimeError(f"{nome} falhou (codigo {p.returncode}); veja {RELATORIOS}")
    return p.stdout, p.returncode


def analisar_bandit(con, ids):
    print("Rodando bandit...")
    saida, _ = rodar([sys.executable, "-m", "bandit", "-f", "json", "-q"] +
                       [os.path.join(PASTA, f"g{i}.py") for i in ids])
    if not saida:
        raise RuntimeError("Ferramenta nao produziu resultado")
    try:
        dados = json.loads(saida)
    except json.JSONDecodeError:
        raise RuntimeError("Saida do bandit ilegivel")

    if dados.get("errors"):
        raise RuntimeError(f"Erros de analise: {dados['errors']}; veja {RELATORIOS}")
    arquivos = dados.get("metrics", {}) if "metrics" in dados else dados.get("paths", {}).get("scanned", [])
    cobertos = {id_do_arquivo(caminho) for caminho in arquivos}
    faltantes = set(ids) - cobertos
    if faltantes:
        raise RuntimeError(f"Cobertura incompleta; geracoes ausentes: {sorted(faltantes)}")
    n = 0
    for r in dados.get("results", []):
        gid = id_do_arquivo(r.get("filename", ""))
        if gid is None:
            continue
        regra = r.get("test_id", "")
        con.execute(
            "INSERT INTO achados (geracao_id, ferramenta, regra, cwe, "
            "severidade, linha, mensagem) VALUES (?,?,?,?,?,?,?)",
            (gid, "bandit", regra, (f"CWE-{r['issue_cwe']['id']}" if (r.get("issue_cwe") or {}).get("id") else BANDIT_CWE.get(regra)),
             r.get("issue_severity"), r.get("line_number"),
             (r.get("issue_text") or "")[:400]),
        )
        n += 1
    return n


def analisar_semgrep(con, ids):
    print(f"Rodando semgrep ({REGRAS_SEMGREP})...")
    saida, _ = rodar([str(Path(sys.executable).with_name("semgrep.exe" if os.name == "nt" else "semgrep")), "--config", REGRAS_SEMGREP, "--json",
                      "--quiet", "--metrics=off", "--disable-version-check", "--no-git-ignore"] +
                      [os.path.join(PASTA, f"g{i}.py") for i in ids])
    if not saida:
        raise RuntimeError("Ferramenta nao produziu resultado")
    try:
        dados = json.loads(saida)
    except json.JSONDecodeError:
        raise RuntimeError("Saida do semgrep ilegivel")

    if dados.get("errors"):
        raise RuntimeError(f"Erros de analise: {dados['errors']}; veja {RELATORIOS}")
    arquivos = dados.get("metrics", {}) if "metrics" in dados else dados.get("paths", {}).get("scanned", [])
    cobertos = {id_do_arquivo(caminho) for caminho in arquivos}
    faltantes = set(ids) - cobertos
    if faltantes:
        raise RuntimeError(f"Cobertura incompleta; geracoes ausentes: {sorted(faltantes)}")
    n = 0
    for r in dados.get("results", []):
        gid = id_do_arquivo(r.get("path", ""))
        if gid is None:
            continue
        extra = r.get("extra", {})
        meta = extra.get("metadata", {})
        cwe_bruto = meta.get("cwe")
        if isinstance(cwe_bruto, list):
            cwe_bruto = cwe_bruto[0] if cwe_bruto else None
        cwe = None
        if cwe_bruto:
            m = CWE_RE.search(str(cwe_bruto))
            cwe = f"CWE-{m.group(1)}" if m else None
        con.execute(
            "INSERT INTO achados (geracao_id, ferramenta, regra, cwe, "
            "severidade, linha, mensagem) VALUES (?,?,?,?,?,?,?)",
            (gid, "semgrep", r.get("check_id", "")[:200], cwe,
             extra.get("severity"), (r.get("start") or {}).get("line"),
             (extra.get("message") or "")[:400]),
        )
        n += 1
    return n


def resumo(con):
    print("\n=== Geracoes analisadas com achados por modelo e nivel ===")
    print(f"{'modelo':<28} {'nivel':<6} {'n':>3} {'c/ achado':>10} {'%':>6} "
          f"{'achados/ger':>12}")
    linhas = con.execute("""
        SELECT g.modelo, g.nivel,
               COUNT(DISTINCT g.id)                                   AS n,
               COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN g.id END) AS com,
               COUNT(a.id)                                            AS total
        FROM geracoes g
        LEFT JOIN achados a ON a.geracao_id = g.id
        WHERE g.erro IS NULL AND g.id IN (SELECT geracao_id FROM analisadas)
        GROUP BY g.modelo, g.nivel
        ORDER BY g.modelo, g.nivel
    """).fetchall()
    for modelo, nivel, n, com, total in linhas:
        pct = 100.0 * com / n if n else 0
        print(f"{modelo:<28} {nivel:<6} {n:>3} {com:>10} {pct:>5.0f}% "
              f"{total / n if n else 0:>12.2f}")

    print("\n=== CWE mais frequentes por nivel ===")
    linhas = con.execute("""
        SELECT COALESCE(a.cwe, '(sem mapa)') AS cwe, g.nivel, COUNT(*) 
        FROM achados a JOIN geracoes g ON g.id = a.geracao_id
        GROUP BY cwe, g.nivel ORDER BY COUNT(*) DESC LIMIT 25
    """).fetchall()
    for cwe, nivel, c in linhas:
        print(f"  {cwe:<14} {nivel:<4} {c:>4}")

    sem_mapa = con.execute(
        "SELECT COUNT(*) FROM achados WHERE cwe IS NULL").fetchone()[0]
    if sem_mapa:
        print(f"\n{sem_mapa} achados sem CWE mapeado - revisar manualmente "
              f"(SELECT DISTINCT ferramenta, regra FROM achados WHERE cwe IS NULL).")

    print("\nLembrete: estes numeros sao de analise estatica e incluem falsos "
          "positivos.\nAusencia de achados nao comprova seguranca; T06 precisa do "
          "verificador comportamental.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--refazer", action="store_true")
    p.add_argument("--resumo", action="store_true")
    args = p.parse_args()

    con = conectar()
    if args.resumo:
        resumo(con)
        con.close()
        return

    ids = exportar(con, args.refazer)
    if not ids:
        print("Nada novo para analisar.")
        resumo(con)
        con.close()
        return
    print(f"{len(ids)} codigos exportados para {PASTA}")

    try:
        marcas = ",".join("?" for _ in ids)
        con.execute(f"DELETE FROM achados WHERE geracao_id IN ({marcas})", ids)
        nb = analisar_bandit(con, ids)
        ns = analisar_semgrep(con, ids)
    except RuntimeError as e:
        con.rollback()
        con.close()
        sys.exit(f"Analise incompleta; geracoes nao marcadas como analisadas. {e}")
    print(f"achados - bandit: {nb} | semgrep: {ns}")

    con.executemany("INSERT OR IGNORE INTO analisadas (geracao_id) VALUES (?)",
                    [(i,) for i in ids])
    con.commit()
    resumo(con)
    con.close()


if __name__ == "__main__":
    main()
