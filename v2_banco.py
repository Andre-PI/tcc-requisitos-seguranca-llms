"""Banco SQLite temporario com dados ficticios, criado antes da importacao da amostra."""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
import tempfile


@contextmanager
def banco(script):
    with tempfile.TemporaryDirectory(prefix='tcc-banco-') as pasta:
        caminho = Path(pasta) / 'dados.db'
        with sqlite3.connect(caminho) as con:
            con.executescript(script)
        anterior = os.environ.get('TCC_DB_PATH')
        os.environ['TCC_DB_PATH'] = str(caminho)
        try:
            yield caminho
        finally:
            if anterior is None:
                os.environ.pop('TCC_DB_PATH', None)
            else:
                os.environ['TCC_DB_PATH'] = anterior


def consultar(caminho, sql, *parametros):
    con = sqlite3.connect(caminho)
    try:
        return con.execute(sql, parametros).fetchall()
    finally:
        con.close()
