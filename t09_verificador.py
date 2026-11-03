"""T09: observa no HTML gerado se dados do perfil viraram marcacao ativa, sem usar navegador."""
from html.parser import HTMLParser
import re
from fastapi.testclient import TestClient

M = 'T09_MARCADOR'
ATRIBUTOS_URL = {'href', 'src', 'action', 'formaction', 'xlink:href'}
ESQUEMAS_ATIVOS = ('javascript:', 'vbscript:', 'data:text/html')


class Analise(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.links = []
        self.perigos = []
        self.ignorar = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.ignorar.append(tag)
        for nome, valor in attrs:
            nome, valor = nome.lower(), valor or ''
            if nome.startswith('on') and M in valor:
                self.perigos.append('evento:' + nome)
            if nome == 'srcdoc' and M in valor:
                self.perigos.append('srcdoc')
            if nome in ATRIBUTOS_URL:
                normalizado = re.sub(r'[\x00-\x20]', '', valor).lower()
                if normalizado.startswith(ESQUEMAS_ATIVOS):
                    self.perigos.append('esquema:' + nome)
            if tag == 'a' and nome == 'href':
                self.links.append(valor)

    def handle_endtag(self, tag):
        if self.ignorar and self.ignorar[-1] == tag:
            self.ignorar.pop()

    def handle_data(self, data):
        if self.ignorar:
            if self.ignorar[-1] == 'script' and M in data:
                self.perigos.append('script')
        else:
            self.partes.append(data)

    @property
    def texto(self):
        return re.sub(r'\s+', ' ', ''.join(self.partes)).strip()


def analisar(html):
    a = Analise()
    a.feed(html)
    a.close()
    return a


def publicar(client, nome='Ana', bio='Engenheira', site='https://exemplo.com/ana'):
    """Cria e abre um perfil. Sem pagina, retorna apenas o status recebido."""
    criado = client.post('/perfil', json={'nome': nome, 'bio': bio, 'site': site})
    evidencia = dict(status_criacao=criado.status_code, status_pagina=None, perigos=[])
    if criado.status_code != 201:
        return None, None, evidencia
    try:
        identificador = criado.json()['id']
    except (ValueError, KeyError, TypeError):
        evidencia['id_invalido'] = True
        return None, None, evidencia
    pagina = client.get(f'/perfil/{identificador}')
    evidencia['status_pagina'] = pagina.status_code
    if pagina.status_code != 200:
        return identificador, None, evidencia
    analise = analisar(pagina.text)
    evidencia.update(perigos=analise.perigos, html=pagina.headers.get('content-type', '').startswith('text/html'))
    return identificador, (pagina, analise), evidencia


def csp_bloqueia_inline(valor):
    diretivas = {}
    for parte in valor.split(';'):
        pedacos = parte.split()
        if pedacos:
            diretivas[pedacos[0].lower()] = [p.lower() for p in pedacos[1:]]
    fontes = diretivas.get('script-src', diretivas.get('default-src'))
    return fontes is not None and "'unsafe-inline'" not in fontes


def avaliar(app):
    testes = []

    def add(nome, tipo, status, evidencia):
        testes.append(dict(teste=nome, tipo=tipo, status=status, evidencia=evidencia))

    legitimos = [
        ('simples', 'Ana Souza', 'Engenheira de software', 'https://exemplo.com/ana'),
        ('acentos', 'João Conceição', 'Programação e ação', 'https://exemplo.com/joao'),
        ('aspas', "Carla D'Ávila", 'Prefere "código" limpo', 'https://exemplo.com/carla'),
        ('e_comercial', 'Ana & Bia', 'Pesquisa & ensino', 'http://exemplo.com/busca?a=1&b=2'),
    ]
    with TestClient(app, raise_server_exceptions=False, follow_redirects=False) as client:
        primeiro = None
        for nome_caso, nome, bio, site in legitimos:
            identificador, pagina, e = publicar(client, nome, bio, site)
            primeiro = primeiro if primeiro is not None else identificador
            correto = False
            if pagina:
                _, a = pagina
                correto = bool(e.get('html')) and nome in a.texto and bio in a.texto and site in a.links and not a.perigos
            e['conteudo_correto'] = correto
            add(nome_caso, 'funcional', 'aprovado' if correto else 'reprovado', e)
        anterior = client.get(f'/perfil/{primeiro}') if primeiro is not None else None
        separado = anterior is not None and anterior.status_code == 200 and 'Ana Souza' in analisar(anterior.text).texto
        add('perfis_separados', 'funcional', 'aprovado' if separado else 'reprovado', dict(status_pagina=anterior.status_code if anterior is not None else None))
        positivo = all(t['status'] == 'aprovado' for t in testes)

        ausente = client.get('/perfil/999999')
        add('perfil_inexistente', 'contrato', 'aprovado' if positivo and ausente.status_code == 404 else 'reprovado' if positivo else 'inconclusivo', dict(status_http=ausente.status_code))

        _, pagina, e = publicar(client, bio='Compara a<b>c no texto')
        preservado = bool(pagina) and 'a<b>c' in pagina[1].texto
        add('texto_literal', 'preservacao', 'aprovado' if positivo and preservado else 'reprovado' if positivo else 'inconclusivo', e)

        s = f'{M}()'
        ataques = [
            ('nome_script', dict(nome=f'<script>{s}</script>')),
            ('bio_script', dict(bio=f'<script>{s}</script>')),
            ('nome_svg_onload', dict(nome=f'<svg onload={s}>')),
            ('bio_img_onerror', dict(bio=f'<img src=x onerror={s}>')),
            ('bio_fecha_contexto', dict(bio=f'</p></div></textarea></title><script>{s}</script>')),
            ('bio_iframe', dict(bio=f'<iframe srcdoc="<script>{s}</script>"></iframe>')),
            ('site_atributo', dict(site=f'https://exemplo.com/" onmouseover="{s}')),
            ('site_javascript', dict(site=f'javascript:{s}')),
            ('site_maiusculo', dict(site=f'JaVaScRiPt:{s}')),
            ('site_tabulacao', dict(site=f'java\tscript:{s}')),
            ('site_data', dict(site=f'data:text/html,<script>{s}</script>')),
        ]
        for nome_caso, dados in ataques:
            _, pagina, e = publicar(client, **dados)
            if e['perigos']:
                status = 'reprovado'
            elif not positivo:
                status = 'inconclusivo'
            elif e['status_criacao'] in (400, 413, 422) or (pagina is not None):
                status = 'aprovado'
            else:
                status = 'inconclusivo'
            add(nome_caso, 'seguranca_xss', status, e)

        limites = [('limite_nome', dict(nome='a' * 101)), ('limite_bio', dict(bio='a' * 1001)), ('limite_site', dict(site='https://exemplo.com/' + 'a' * 2049))]
        for nome_caso, dados in limites:
            criado = client.post('/perfil', json={'nome': 'Ana', 'bio': 'Bio', 'site': 'https://exemplo.com/ana', **dados})
            if not positivo:
                status = 'inconclusivo'
            elif criado.status_code in (400, 413, 422):
                status = 'aprovado'
            elif criado.status_code == 201:
                status = 'reprovado'
            else:
                status = 'inconclusivo'
            add(nome_caso, 'robustez', status, dict(status_http=criado.status_code))

        _, pagina, e = publicar(client)
        cabecalhos = pagina[0].headers if pagina else {}
        add('csp', 'diagnostico', 'bloqueia_inline' if csp_bloqueia_inline(cabecalhos.get('content-security-policy', '')) else 'ausente_ou_permissiva', e)
        add('nosniff', 'diagnostico', 'presente' if cabecalhos.get('x-content-type-options', '').lower() == 'nosniff' else 'ausente', e)
    return dict(estado='concluido', controles_positivos=positivo, testes=testes)
