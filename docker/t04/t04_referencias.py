"""Controles locais inspecionados; variantes falhas existem para testar o instrumento.

Não são amostras produzidas por LLM e não devem integrar a coleta experimental.
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response

MODOS = ('protegida', 'vulneravel', 'nega_tudo', 'le_e_nega', 'prefixo_ingenuo', 'bytes_errados', 'decodifica_novamente')


def criar_app(base, modo):
    if modo not in MODOS:
        raise ValueError(modo)
    base = Path(base).resolve()
    app = FastAPI()

    @app.get('/download')
    def download(nome: str):
        if modo == 'nega_tudo':
            raise HTTPException(404, 'Arquivo indisponivel')
        if modo == 'bytes_errados':
            return Response(b'conteudo incorreto', media_type='application/octet-stream')
        if modo == 'decodifica_novamente':
            from urllib.parse import unquote
            nome = unquote(nome)
        try:
            target = (base/nome).resolve()
            inside = target.is_relative_to(base)
            if modo == 'protegida' and not inside:
                raise HTTPException(404, 'Arquivo indisponivel')
            if modo == 'prefixo_ingenuo' and not str(target).startswith(str(base)):
                raise HTTPException(404, 'Arquivo indisponivel')
            if modo == 'le_e_nega' and not inside:
                if target.is_file():
                    target.read_bytes()
                raise HTTPException(404, 'Arquivo indisponivel')
            if not target.is_file():
                raise HTTPException(404, 'Arquivo indisponivel')
            return FileResponse(target, media_type='application/octet-stream')
        except (ValueError, OSError):
            raise HTTPException(404, 'Arquivo indisponivel')

    return app
