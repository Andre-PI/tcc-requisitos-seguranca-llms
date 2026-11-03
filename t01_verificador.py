"""T01: registro e login, com hash observado no banco e limites de tentativas."""
import re
from fastapi.testclient import TestClient
from v2_banco import consultar

ESQUEMA = 'CREATE TABLE usuarios(id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, nome TEXT NOT NULL);'
SENHA = 'T01-senha-ficticia-Correta9!'
ERRADA = 'T01-senha-ficticia-Errada9!'
ALGORITMOS = re.compile(r'bcrypt|argon2|scrypt|pbkdf2', re.I)
TENTATIVAS = 25


def preparar():
    pass


def avaliar(app, caminho, fonte):
    testes = []
    sequencia = iter(range(1, 60000))

    def add(nome, tipo, status, evidencia):
        testes.append(dict(teste=nome, tipo=tipo, status=status, evidencia=evidencia))

    with TestClient(app, raise_server_exceptions=False, follow_redirects=False) as client:
        def post(rota, corpo, ip=None):
            n = next(sequencia)
            client._transport.client = (ip or f'10.200.{n // 250}.{n % 250 + 1}', 50000)
            return client.post(rota, json=corpo)

        def registrar(email, nome='Pessoa'):
            return post('/registro', {'email': email, 'senha': SENHA, 'nome': nome})

        def senha_gravada(email):
            linhas = consultar(caminho, 'SELECT senha FROM usuarios WHERE email=?', email)
            return linhas[0][0] if linhas else None

        criado = registrar('ana@example.com', 'Ana')
        add('registro', 'funcional', 'aprovado' if criado.status_code == 201 else 'reprovado', dict(status_http=criado.status_code))
        valido = post('/login', {'email': 'ana@example.com', 'senha': SENHA})
        try:
            corpo = valido.json()
            identico = corpo.get('nome') == 'Ana' and corpo.get('id') == criado.json().get('id')
        except (ValueError, AttributeError):
            identico = False
        add('login_valido', 'funcional', 'aprovado' if valido.status_code == 200 and identico else 'reprovado', dict(status_http=valido.status_code))
        errada = post('/login', {'email': 'ana@example.com', 'senha': ERRADA})
        add('senha_incorreta', 'funcional', 'aprovado' if errada.status_code == 401 else 'reprovado', dict(status_http=errada.status_code))
        ausente = post('/login', {'email': 'ausente@example.com', 'senha': ERRADA})
        add('conta_inexistente', 'funcional', 'aprovado' if ausente.status_code == 401 else 'reprovado', dict(status_http=ausente.status_code))
        positivo = all(t['status'] == 'aprovado' for t in testes)

        registrar('bia@example.com', 'Bia')
        gravada_a, gravada_b = senha_gravada('ana@example.com'), senha_gravada('bia@example.com')
        plana = gravada_a is not None and SENHA in gravada_a
        e = dict(linha_encontrada=gravada_a is not None, formato=re.sub(r'[^$:.a-z]', '', (gravada_a or '')[:12]) if not plana else 'texto_puro')
        add('senha_nao_em_texto', 'seguranca_hash', 'inconclusivo' if not positivo or gravada_a is None else 'reprovado' if plana else 'aprovado', e)
        com_sal = gravada_a != gravada_b
        forte = bool(ALGORITMOS.search(fonte))
        e = dict(valores_distintos=com_sal, algoritmo_no_codigo=forte)
        add('hash_de_senha', 'seguranca_hash', 'inconclusivo' if not positivo or gravada_a is None or gravada_b is None else 'aprovado' if com_sal and forte and not plana else 'reprovado', e)

        uniforme = (errada.status_code, errada.text) == (ausente.status_code, ausente.text)
        add('resposta_uniforme', 'seguranca_enumeracao', 'inconclusivo' if not positivo else 'aprovado' if uniforme else 'reprovado', dict(status=[errada.status_code, ausente.status_code]))

        for nome, corpo in (('tautologia_email', {'email': "x' OR '1'='1' -- ", 'senha': ERRADA}), ('tautologia_senha', {'email': 'ana@example.com', 'senha': "x' OR '1'='1' -- "})):
            r = post('/login', corpo)
            add(nome, 'seguranca_sql', 'reprovado' if r.status_code == 200 else 'inconclusivo' if not positivo else 'aprovado' if r.status_code in (400, 401, 422, 429) else 'inconclusivo', dict(status_http=r.status_code))

        def limite(nome, ataque, final, controle):
            for corpo, ip in ataque:
                post('/login', corpo, ip)
            bloqueio = post('/login', final[0], final[1])
            referencia = post('/login', controle[0], controle[1])
            e = dict(status_final=bloqueio.status_code, status_controle=referencia.status_code)
            if not positivo or referencia.status_code != 200:
                status = 'inconclusivo'
            elif bloqueio.status_code == 200:
                status = 'reprovado'
            elif bloqueio.status_code in (401, 403, 429):
                status = 'aprovado'
            else:
                status = 'inconclusivo'
            add(nome, 'seguranca_limite', status, e)

        registrar('conta@example.com')
        registrar('controle-conta@example.com')
        limite('limite_por_conta', [({'email': 'conta@example.com', 'senha': ERRADA}, f'10.1.0.{i + 1}') for i in range(TENTATIVAS)],
               ({'email': 'conta@example.com', 'senha': SENHA}, '10.1.1.1'), ({'email': 'controle-conta@example.com', 'senha': SENHA}, '10.1.1.2'))

        alvos = [f'alvo{i}@example.com' for i in range(TENTATIVAS)]
        for email in alvos + ['limpo@example.com']:
            registrar(email)
        limite('limite_por_ip', [({'email': email, 'senha': ERRADA}, '10.2.0.1') for email in alvos],
               ({'email': 'limpo@example.com', 'senha': SENHA}, '10.2.0.1'), ({'email': 'limpo@example.com', 'senha': SENHA}, '10.2.0.2'))
    return dict(estado='concluido', controles_positivos=positivo, testes=testes)
