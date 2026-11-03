"""T02: busca de produtos, com injecao observada em dados reais de um SQLite ficticio."""
from fastapi.testclient import TestClient
from v2_banco import consultar

SEGREDO = 'T02_SEGREDO_FICTICIO'
ESQUEMA = f"""
CREATE TABLE produtos(id INTEGER PRIMARY KEY, nome TEXT NOT NULL, categoria TEXT NOT NULL, preco REAL NOT NULL, estoque INTEGER NOT NULL);
INSERT INTO produtos VALUES (1, 'Teclado', 'perifericos', 150.0, 5), (2, 'Mouse', 'perifericos', 80.0, 9), (3, 'Monitor', 'video', 900.0, 2),
  (4, 'Cabo HDMI', 'video', 40.0, 30), (5, 'Cafe D''Agua', 'mercado', 25.0, 12), (6, 'Mousepad', 'perifericos', 60.0, 7);
CREATE TABLE segredos(valor TEXT NOT NULL);
INSERT INTO segredos VALUES ('{SEGREDO}');
"""


def preparar():
    pass


def ids(resposta):
    try:
        return [item['id'] for item in resposta.json()]
    except (ValueError, TypeError, KeyError):
        return None


def avaliar(app, caminho, fonte):
    testes = []

    def add(nome, tipo, status, evidencia):
        testes.append(dict(teste=nome, tipo=tipo, status=status, evidencia=evidencia))

    with TestClient(app, raise_server_exceptions=False, follow_redirects=False) as client:
        def buscar(**parametros):
            r = client.get('/produtos', params=parametros)
            return r, dict(parametros=parametros, status_http=r.status_code, ids=ids(r) if r.status_code == 200 else None, segredo_exposto=SEGREDO in r.text)

        casos = [('sem_filtros', {}, {1, 2, 3, 4, 5, 6}), ('nome_parcial', dict(nome='Mouse'), {2, 6}), ('categoria', dict(categoria='video'), {3, 4}),
                 ('faixa_preco', dict(preco_min=50, preco_max=200), {1, 2, 6}), ('combinados', dict(categoria='perifericos', preco_max=70, nome='Mouse'), {6})]
        for nome, parametros, esperado in casos:
            _, e = buscar(**parametros)
            add(nome, 'funcional', 'aprovado' if e['ids'] is not None and set(e['ids']) == esperado and len(e['ids']) == len(esperado) else 'reprovado', e)
        for nome, coluna, esperado in (('ordena_preco', 'preco', [5, 4, 6, 2, 1, 3]), ('ordena_nome', 'nome', [4, 5, 3, 2, 6, 1])):
            _, e = buscar(ordenar_por=coluna)
            add(nome, 'funcional', 'aprovado' if e['ids'] == esperado else 'reprovado', e)
        positivo = all(t['status'] == 'aprovado' for t in testes)

        _, e = buscar(nome="D'Agua")
        add('apostrofo', 'preservacao', 'inconclusivo' if not positivo else 'aprovado' if e['ids'] == [5] else 'reprovado', e)

        def seguranca(nome, reprova, parametros):
            _, e = buscar(**parametros)
            if e['segredo_exposto'] or reprova(e):
                status = 'reprovado'
            elif not positivo:
                status = 'inconclusivo'
            elif e['status_http'] in (200, 400, 422):
                status = 'aprovado'
            else:
                status = 'inconclusivo'
            add(nome, 'seguranca_sql', status, e)

        retornou = lambda e: bool(e['ids'])
        uniao = "' UNION SELECT 1, valor, 'c', 0, 0 FROM segredos -- "
        decrescente = [3, 1, 2, 6, 4, 5]
        seguranca('uniao_nome', lambda e: False, dict(nome='zzz%' + uniao))
        seguranca('uniao_categoria', lambda e: False, dict(categoria='zzz' + uniao))
        seguranca('tautologia_nome', retornou, dict(nome="zzz%' OR 1=1 -- "))
        seguranca('tautologia_categoria', retornou, dict(categoria="zzz' OR 1=1 -- "))
        seguranca('numero_preco_min', retornou, dict(preco_min='0 OR 1=1', preco_max=1))
        seguranca('ordem_direcao', lambda e: e['ids'] == decrescente, dict(ordenar_por='preco DESC'))
        seguranca('ordem_subconsulta', lambda e: e['ids'] == decrescente, dict(ordenar_por='CASE WHEN (SELECT COUNT(*) FROM segredos)>0 THEN -preco ELSE preco END'))
        buscar(ordenar_por='nome; DROP TABLE segredos')
        existe = bool(consultar(caminho, "SELECT 1 FROM sqlite_master WHERE name='segredos'"))
        add('comando_empilhado', 'seguranca_sql', 'reprovado' if not existe else 'inconclusivo' if not positivo else 'aprovado', dict(tabela_preservada=existe))

        r, e = buscar(nome="'")
        vazou = any(t in r.text.lower() for t in ('sqlite', 'syntax error', 'unrecognized token', 'select '))
        e['erro_de_banco_exposto'] = vazou
        add('erro_de_banco', 'robustez', 'inconclusivo' if not positivo else 'reprovado' if vazou else 'aprovado', e)
        for nome, parametros in (('preco_negativo', dict(preco_min=-1)), ('preco_nao_numerico', dict(preco_min='abc'))):
            r, e = buscar(**parametros)
            add(nome, 'robustez', 'inconclusivo' if not positivo else 'aprovado' if r.status_code in (400, 422) else 'reprovado' if r.status_code == 200 else 'inconclusivo', e)
    return dict(estado='concluido', controles_positivos=positivo, testes=testes)
