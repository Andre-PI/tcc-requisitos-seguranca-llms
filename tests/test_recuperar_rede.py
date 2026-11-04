import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import recuperar_rede as r


def gravar(base, gid, dados):
    (base / gid).mkdir()
    (base / gid / 'geracao.json').write_text(json.dumps(dados), encoding='utf-8')


def test_so_seleciona_falha_de_transporte_sem_resposta(tmp_path, monkeypatch):
    monkeypatch.setattr(r, 'DATA', tmp_path)
    fim = {'concluida_em': 'x'}
    gravar(tmp_path, 'rede', {**fim, 'resposta': None, 'tentativas': [{'erro': 'URLError'}, {'erro': 'TimeoutError'}]})
    gravar(tmp_path, 'http500', {**fim, 'resposta': None, 'tentativas': [{'http': 500, 'erro': 'x'}, {'http': 503, 'erro': 'x'}]})
    gravar(tmp_path, 'modelo', {**fim, 'resposta': {'id': 1}, 'erro': 'SyntaxError', 'tentativas': [{'http': 200}]})
    gravar(tmp_path, 'cortada', {**fim, 'resposta': {'id': 2}, 'erro': 'incompleta', 'tentativas': [{'http': 200}]})
    gravar(tmp_path, 'aberta', {'resposta': None, 'tentativas': [{'erro': 'URLError'}]})
    jobs = [{'id': i} for i in ('rede', 'http500', 'modelo', 'cortada', 'aberta', 'ausente')]
    assert r.sem_resposta(jobs) == ['rede']


def test_sem_resposta_interrompe_em_vez_de_registrar():
    com_falha = r.chamar_sem_registrar_falha(lambda *a, **k: ({}, None))
    with pytest.raises(r.c.Parada):
        com_falha('m', 'p', [])


def test_resposta_normal_passa_sem_alteracao():
    assert r.chamar_sem_registrar_falha(lambda *a, **k: ({'c': 1}, {'r': 2}))('m', 'p', []) == ({'c': 1}, {'r': 2})
