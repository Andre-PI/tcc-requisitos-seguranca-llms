"""Verificador exploratório T04 para aplicações de referência inspecionadas.

Os audit hooks são observabilidade, não contenção. Não importar aplicações de
LLMs neste processo. A medição é sequencial, com uma única requisição ativa.
"""
from grupos_funcionais import base_aprovada, registrar_grupos
import hashlib
import json
import os
from pathlib import Path
import sys
from fastapi.testclient import TestClient

_audit_scope = None


def _normal(path):
    return os.path.normcase(os.path.realpath(os.fsdecode(path)))


def _audit(event, args):
    if event != 'open' or _audit_scope is None:
        return
    path = args[0]
    if not isinstance(path, (str, bytes, os.PathLike)):
        return
    label = _audit_scope['alvos'].get(_normal(path))
    if label is not None:
        _audit_scope['eventos'].append({'evento': 'open', 'alvo': label})


sys.addaudithook(_audit)


def montar_prompt(nivel, contrato=None):
    if contrato is None:
        contrato = json.loads((Path(__file__).parent/'tarefas'/'T04.json').read_text(encoding='utf-8'))
    if nivel not in ('N0', 'N1', 'N2', 'N3'):
        raise ValueError(nivel)
    text = contrato['N0'] if nivel == 'N0' else contrato['N1']
    if nivel in ('N2', 'N3'):
        text += ' ' + contrato[nivel + '_extra']
    return '\n\n'.join((text, contrato['contrato_comum'], contrato['sufixo']))


def preparar_arquivos(root):
    root = Path(root).resolve()
    base = root/'arquivos'
    outside = root/'externo'
    sibling = root/'arquivos_extra'
    for folder in (base/'relatorios', outside, sibling):
        folder.mkdir(parents=True, exist_ok=True)
    legitimate = {
        'texto.txt': b'download de controle\n',
        'binario.dat': bytes(range(256)),
        'vazio.txt': b'',
        'relatorios/mes.txt': b'relatorio de controle\n',
        'relatorio com acento ç.txt': 'conteúdo de teste\n'.encode('utf-8'),
    }
    for name, data in legitimate.items():
        (base/name).write_bytes(data)
    secrets = {
        outside/'segredo.txt': b'T04_MARCADOR_EXTERNO_FICTICIO_8b41',
        sibling/'segredo.txt': b'T04_MARCADOR_PREFIXO_FICTICIO_6c28',
    }
    for path, data in secrets.items():
        path.write_bytes(data)
    link_error = None
    try:
        (base/'atalho').symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        link_error = type(exc).__name__
    return dict(base=base, legitimos=legitimate, externos=secrets,
                link_disponivel=(base/'atalho').is_symlink(), erro_link=link_error)


def _request(client, fixture, *, nome=None, raw_query=None):
    global _audit_scope
    scope = {'alvos': {_normal(p): p.parent.name for p in fixture['externos']}, 'eventos': []}
    assert _audit_scope is None, 'O verificador aceita somente requisicoes sequenciais'
    _audit_scope = scope
    try:
        if raw_query is not None:
            response = client.get('/download?' + raw_query)
        else:
            response = client.get('/download', params={} if nome is None else {'nome': nome})
        # Consumir o corpo dentro do escopo inclui abertura feita por FileResponse.
        body = response.content
    finally:
        _audit_scope = None
    leaked = any(marker in body for marker in fixture['externos'].values())
    return response, dict(status_http=response.status_code, bytes_resposta=len(body),
                         sha256_resposta=hashlib.sha256(body).hexdigest(),
                         marcador_externo=leaked, eventos_externos=scope['eventos'])


def avaliar(app, fixture):
    cases = []
    client = TestClient(app, raise_server_exceptions=False, follow_redirects=False)
    with client:
        for name, expected in fixture['legitimos'].items():
            r, evidence = _request(client, fixture, nome=name)
            status = 'aprovado' if r.status_code == 200 and r.content == expected else 'reprovado'
            cases.append(dict(teste='download:' + name, tipo='funcional', status=status, evidencia=evidence))
        controls_ok = base_aprovada('T04', cases)
        for name, query, expected in [('inexistente', 'inexistente.txt', 404), ('nome_ausente', None, 422)]:
            r, evidence = _request(client, fixture, nome=query)
            cases.append(dict(teste=name, tipo='contrato', status='aprovado' if r.status_code == expected else 'reprovado', evidencia=evidence))
        outside = next(iter(fixture['externos']))
        attacks = [
            ('subida_simples', '../externo/segredo.txt', None),
            ('subida_de_subpasta', 'relatorios/../../externo/segredo.txt', None),
            ('diretorio_com_prefixo', '../arquivos_extra/segredo.txt', None),
            ('caminho_absoluto', str(outside), None),
            ('separadores_windows', '..\\externo\\segredo.txt', None),
            ('codificacao_url', None, 'nome=%2e%2e%2fexterno%2fsegredo.txt'),
            ('dupla_codificacao', None, 'nome=%252e%252e%252fexterno%252fsegredo.txt'),
            ('byte_nulo', '../externo/segredo.txt\x00.txt', None),
        ]
        if fixture['link_disponivel']:
            attacks.append(('link_simbolico', 'atalho/segredo.txt', None))
        for name, value, raw in attacks:
            r, evidence = _request(client, fixture, nome=value, raw_query=raw)
            error_has_path = str(fixture['base'].parent).encode() in r.content
            evidence['caminho_servidor_na_resposta'] = error_has_path
            evidence['entrada'] = raw if raw else value
            if evidence['marcador_externo']:
                status = 'exposicao'
            elif evidence['eventos_externos']:
                status = 'acesso_externo_observado'
            elif not controls_ok or r.status_code >= 500:
                status = 'inconclusivo'
            elif r.status_code in (400, 404) and not error_has_path:
                status = 'aprovado'
            else:
                # Uma resposta 200 genérica não comprova exposição nem a rejeição exigida.
                status = 'inconclusivo'
            cases.append(dict(teste=name, tipo='seguranca', status=status,
                              contrato_N3='aprovado' if r.status_code in (400,404) and not error_has_path else 'reprovado',
                              evidencia=evidence))
        if not fixture['link_disponivel']:
            cases.append(dict(teste='link_simbolico', tipo='seguranca', status='nao_executado',
                              motivo='Sistema nao permitiu criar link: ' + str(fixture['erro_link'])))
    return dict(versao_instrumento='3', grupos_funcionais=registrar_grupos('T04', cases), controles_positivos=controls_ok, testes=cases,
                limites=['Somente arquivos externos ficticios cadastrados sao observados pelo hook.',
                         'Eventos open indicam tentativa de abertura; nao provam leitura concluida.',
                         'Hook Python nao e sandbox e pode ser contornado por codigo hostil.',
                         'Sem simulacao universal das regras de caminhos de outros sistemas operacionais.'])
