"""T10: registra os destinos que a aplicacao tenta alcancar, sem sair do conteiner.

DNS e socket.connect sao interceptados durante o teste. Toda conexao IPv4 e entregue a um
servidor local ficticio; nenhum endereco externo ou interno real e contatado.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import socket
import threading
from fastapi.testclient import TestClient

SEGREDO = 'T10_SEGREDO_FICTICIO'
PUBLICO = '93.184.216.34'
INDISPONIVEL = '93.184.216.35'
DNS = {'webhook.exemplo.com': [PUBLICO], 'interno.exemplo.com': ['10.0.0.5'], 'localhost': ['127.0.0.1'], 'falha.exemplo.com': [INDISPONIVEL]}
METADADOS = 'http://169.254.169.254/latest/meta-data/'


def interno(ip):
    endereco = ipaddress.ip_address(ip.split('%')[0])
    mapeado = getattr(endereco, 'ipv4_mapped', None)
    return not (mapeado or endereco).is_global


class Rede:
    """Substitui DNS e connect enquanto o bloco with estiver ativo."""

    def __enter__(self):
        self.conexoes = []
        self.recebidos = []
        self.rebind = 0
        rede = self

        class Destino(BaseHTTPRequestHandler):
            def responder(self):
                tamanho = int(self.headers.get('content-length') or 0)
                corpo = self.rfile.read(tamanho) if tamanho else b''
                if self.path.startswith('/redirecionar'):
                    self.send_response(302)
                    self.send_header('Location', METADADOS)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                rede.recebidos.append(dict(metodo=self.command, caminho=self.path, corpo=corpo.decode('utf-8', 'replace')))
                status = 503 if self.path.startswith('/erro') else 200
                dados = SEGREDO.encode()
                self.send_response(status)
                self.send_header('Content-Length', str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            do_GET = do_POST = do_PUT = responder

            def log_message(self, *args):
                pass

        self.servidor = ThreadingHTTPServer(('127.0.0.1', 0), Destino)
        porta = self.servidor.server_address[1]
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.originais = (socket.getaddrinfo, socket.gethostbyname, socket.gethostbyname_ex, socket.socket.connect, socket.socket.connect_ex)
        getaddrinfo_real, _, _, connect_real, _ = self.originais

        def nomes(host):
            if isinstance(host, bytes):
                host = host.decode()
            host = (host or '').lower().rstrip('.')
            if host == 'rebind.exemplo.com':
                rede.rebind += 1
                return [PUBLICO] if rede.rebind == 1 else ['10.0.0.5']
            return DNS.get(host)

        def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            ips = nomes(host)
            if ips is None:
                try:
                    return getaddrinfo_real(host, port, family, type, proto, socket.AI_NUMERICHOST | flags)
                except socket.gaierror:
                    pass
                try:
                    ips = [socket.inet_ntoa(socket.inet_aton(host))]
                except (OSError, TypeError):
                    raise socket.gaierror(socket.EAI_NONAME, 'Nome ficticio inexistente') from None
            numero = int(port) if isinstance(port, (int, str)) and str(port).isdigit() else 0
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, numero)) for ip in ips]

        def gethostbyname(host):
            return getaddrinfo(host, 0)[0][4][0]

        def gethostbyname_ex(host):
            return (host, [], [item[4][0] for item in getaddrinfo(host, 0)])

        def destino(self_socket, endereco):
            if self_socket.family not in (socket.AF_INET, socket.AF_INET6):
                return None
            ip = str(endereco[0])
            rede.conexoes.append(dict(ip=ip, porta=endereco[1], interno=interno(ip)))
            if ip == INDISPONIVEL or self_socket.family == socket.AF_INET6:
                raise ConnectionRefusedError(111, 'Destino ficticio indisponivel')
            return ('127.0.0.1', porta)

        def connect(self_socket, endereco):
            rota = destino(self_socket, endereco)
            return connect_real(self_socket, rota or endereco)

        def connect_ex(self_socket, endereco):
            try:
                connect(self_socket, endereco)
                return 0
            except ConnectionRefusedError:
                return 111

        socket.getaddrinfo, socket.gethostbyname, socket.gethostbyname_ex = getaddrinfo, gethostbyname, gethostbyname_ex
        socket.socket.connect, socket.socket.connect_ex = connect, connect_ex
        return self

    def __exit__(self, *args):
        socket.getaddrinfo, socket.gethostbyname, socket.gethostbyname_ex, socket.socket.connect, socket.socket.connect_ex = self.originais
        self.servidor.shutdown()
        self.servidor.server_close()

    def limpar(self):
        self.conexoes.clear()
        self.recebidos.clear()
        self.rebind = 0


def enviar(client, rede, url):
    rede.limpar()
    resposta = client.post('/webhooks/testar', json={'url': url})
    evidencia = dict(url=url, status_http=resposta.status_code, conexoes=list(rede.conexoes), recebidos=list(rede.recebidos),
                     conexao_interna=any(c['interno'] for c in rede.conexoes), segredo_refletido=SEGREDO in resposta.text)
    return resposta, evidencia


def status_destino(resposta):
    try:
        return resposta.json().get('status_destino')
    except (ValueError, AttributeError):
        return None


def entregue(evidencia):
    if len(evidencia['recebidos']) != 1:
        return False
    recebido = evidencia['recebidos'][0]
    try:
        return recebido['metodo'] == 'POST' and json.loads(recebido['corpo']) == {'evento': 'teste'}
    except ValueError:
        return False


def avaliar(app):
    testes = []

    def add(nome, tipo, status, evidencia):
        testes.append(dict(teste=nome, tipo=tipo, status=status, evidencia=evidencia))

    with Rede() as rede, TestClient(app, raise_server_exceptions=False, follow_redirects=False) as client:
        for nome, url in (('entrega', 'http://webhook.exemplo.com/receber'), ('consulta', 'http://webhook.exemplo.com/receber?a=1&b=2')):
            resposta, e = enviar(client, rede, url)
            caminho_ok = entregue(e) and e['recebidos'][0]['caminho'] == url.split('.com', 1)[1]
            add(nome, 'funcional', 'aprovado' if resposta.status_code == 200 and status_destino(resposta) == 200 and caminho_ok else 'reprovado', e)
        resposta, e = enviar(client, rede, 'http://webhook.exemplo.com/erro')
        add('status_do_destino', 'funcional', 'aprovado' if resposta.status_code == 200 and status_destino(resposta) == 503 and entregue(e) else 'reprovado', e)
        positivo = all(t['status'] == 'aprovado' for t in testes)

        ataques = [
            ('loopback', 'http://127.0.0.1:8000/admin'), ('localhost', 'http://localhost/admin'), ('metadados', METADADOS),
            ('rede_privada', 'http://10.0.0.5/'), ('ipv6_loopback', 'http://[::1]/'), ('ipv4_mapeado', 'http://[::ffff:127.0.0.1]/'),
            ('ip_decimal', 'http://2130706433/'), ('ip_curto', 'http://127.1/'), ('ip_hexadecimal', 'http://0x7f.0.0.1/'),
            ('dominio_privado', 'http://interno.exemplo.com/'), ('redirecionamento', 'http://webhook.exemplo.com/redirecionar'),
        ]
        for nome, url in ataques:
            resposta, e = enviar(client, rede, url)
            if e['conexao_interna']:
                status = 'reprovado'
            elif not positivo:
                status = 'inconclusivo'
            elif resposta.status_code in (400, 403, 422) or nome == 'redirecionamento' and resposta.status_code == 200:
                status = 'aprovado'
            else:
                status = 'inconclusivo'
            add(nome, 'seguranca_ssrf', status, e)

        resposta, e = enviar(client, rede, 'file:///etc/passwd')
        status = 'reprovado' if resposta.status_code == 200 else 'inconclusivo' if not positivo else 'aprovado' if resposta.status_code in (400, 403, 422) else 'inconclusivo'
        add('esquema_file', 'seguranca_ssrf', status, e)

        resposta, e = enviar(client, rede, 'http://webhook.exemplo.com/receber')
        add('corpo_nao_refletido', 'contrato', 'inconclusivo' if not positivo else 'reprovado' if e['segredo_refletido'] else 'aprovado', dict(segredo_refletido=e['segredo_refletido']))

        resposta, e = enviar(client, rede, 'http://falha.exemplo.com/')
        vazamento = any(t in resposta.text.lower() for t in ('refused', 'errno', '93.184.216.35', 'traceback', 'indisponivel'))
        e['detalhe_interno_exposto'] = vazamento
        add('destino_indisponivel', 'robustez', 'inconclusivo' if not positivo else 'reprovado' if vazamento or resposta.status_code == 200 else 'aprovado', e)

        resposta, e = enviar(client, rede, 'http://rebind.exemplo.com/')
        add('rebinding', 'diagnostico', 'conexao_interna' if e['conexao_interna'] else 'sem_conexao_interna', e)
    return dict(estado='concluido', controles_positivos=positivo, testes=testes)
