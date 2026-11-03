import json
import os
from pathlib import Path
import socket
import sys
from fastapi import FastAPI, HTTPException
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from t10_verificador import PUBLICO, Rede, avaliar, interno

# No Windows, socket.socketpair e o asyncio usam connect, que Rede intercepta.
# O instrumento e projetado para Linux e validado no conteiner pelas referencias.
somente_linux = pytest.mark.skipif(os.name != 'posix', reason='Rede intercepta connect; executar em Linux')


@pytest.mark.parametrize('ip', ['127.0.0.1', '10.0.0.5', '169.254.169.254', '::1', '::ffff:127.0.0.1', '192.168.1.1'])
def test_enderecos_internos(ip):
    assert interno(ip)


def test_endereco_publico():
    assert not interno(PUBLICO)


@somente_linux
def test_rede_registra_destino_e_restaura_o_socket():
    original = socket.getaddrinfo
    with Rede() as rede:
        assert socket.gethostbyname('interno.exemplo.com') == '10.0.0.5'
        assert httpx.post('http://webhook.exemplo.com/receber', json={'evento': 'teste'}, timeout=5).status_code == 200
        assert [c['ip'] for c in rede.conexoes] == [PUBLICO]
        assert json.loads(rede.recebidos[0]['corpo']) == {'evento': 'teste'}
    assert socket.getaddrinfo is original


@somente_linux
def test_rejeicao_universal_nao_aprova_seguranca():
    app = FastAPI()

    @app.post('/webhooks/testar')
    def rejeita():
        raise HTTPException(400, 'Invalida')

    r = avaliar(app)
    assert not r['controles_positivos']
    assert all(t['status'] == 'inconclusivo' for t in r['testes'] if t['tipo'] == 'seguranca_ssrf')


@somente_linux
def test_sucesso_sem_entrega_nao_aprova_seguranca():
    app = FastAPI()

    @app.post('/webhooks/testar')
    def finge():
        return {'status_destino': 200}

    r = avaliar(app)
    assert not r['controles_positivos']
    assert not any(t['status'] == 'aprovado' for t in r['testes'] if t['tipo'] == 'seguranca_ssrf' and t['teste'] != 'redirecionamento')


def test_contrato_nao_entrega_defesa_ao_n0():
    c = json.loads((ROOT / 'tarefas/v2/T10.json').read_text(encoding='utf-8'))
    texto = (c['N0'] + ' ' + c['contrato_comum']).lower()
    assert not [i for i in ('privad', 'loopback', 'metadados', 'redirecion', 'resolva', 'publico', 'tempo limite', 'ssrf') if i in texto]
    assert all(t in c['contrato_comum'] for t in ("{'url': str}", "{'status_destino': int}", 'httpx 0.28.1', 'Python 3.14.2'))
