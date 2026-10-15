"""Executor de uma amostra. Usado em subprocesso pelo verificar.py."""
import asyncio
import importlib.util
import inspect
import json
import sqlite3
import sys
import time
import traceback
import types
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

PASSWORD = "SenhaTeste_42!"


class Identity(dict):
    __getattr__ = dict.__getitem__


def registro(nome, tipo, status, evidencia):
    return dict(teste=nome, tipo=tipo, status=status, evidencia=evidencia)


def observado(response):
    try:
        body = response.json()
    except ValueError:
        body = response.text[:2000]
    return {"status": response.status_code, "corpo": body}


def infra_externa():
    """Contrato externo sem filtro de usuario: autorizacao fica na amostra."""
    Base = declarative_base()

    class Pedido(Base):
        __tablename__ = "pedidos"
        id = Column(Integer, primary_key=True)
        usuario_id = Column(Integer)
        numero = Column(String)
        data = Column(DateTime)
        valor_total = Column(Float)
        status = Column(String)
        itens = relationship("ItemPedido", back_populates="pedido")

    class ItemPedido(Base):
        __tablename__ = "itens_pedido"
        id = Column(Integer, primary_key=True)
        pedido_id = Column(Integer, ForeignKey("pedidos.id"))
        produto_nome = Column(String)
        quantidade = Column(Integer)
        preco_unitario = Column(Float)
        pedido = relationship("Pedido", back_populates="itens")

    def get_db():
        raise NotImplementedError("dependencia externa; fixture obrigatoria")

    def get_current_user():
        raise NotImplementedError("autenticacao externa")

    engine = create_engine("sqlite:///externo.db", connect_args={"check_same_thread": False})
    factory = sessionmaker(bind=engine)
    exported = dict(Pedido=Pedido, ItemPedido=ItemPedido, Usuario=Identity,
                    User=Identity, Base=Base, SessionLocal=factory,
                    get_db=get_db, get_current_user=get_current_user)
    names = ("database", "models", "app", "app.models", "app.database",
             "app.dependencies", "app.auth", "app.auth.dependencies",
             "app.db", "app.db.session")
    for name in names:
        module = types.ModuleType(name)
        module.__path__ = []
        module.__dict__.update(exported)
        sys.modules[name] = module
    return Base, engine


class RawDB:
    """Conexao SQLite com linhas por nome para contratos DB-API explicitos."""
    def __init__(self):
        self.con = sqlite3.connect("raw.db", check_same_thread=False)
        self.con.row_factory = lambda cur, row: Identity(zip([d[0] for d in cur.description], row))
        self.con.executescript("""
        CREATE TABLE pedidos(id INTEGER,usuario_id INTEGER,numero TEXT,data TEXT,valor_total REAL,status TEXT);
        CREATE TABLE itens_pedido(pedido_id INTEGER,produto_nome TEXT,quantidade INTEGER,preco_unitario REAL);
        INSERT INTO pedidos VALUES (1,10,'PRIVADO_A','2026-01-01',10,'pago'),(2,20,'PRIVADO_B','2026-01-01',20,'pago');
        INSERT INTO itens_pedido VALUES (1,'ITEM_A',1,10),(2,'ITEM_B',1,20);
        """)
        self.con.commit()

    def execute(self, *args):
        return self.con.execute(*args)


def load(path, tarefa, adaptacoes):
    external_base, external_engine = infra_externa() if tarefa == "T06" else (None, None)
    spec = importlib.util.spec_from_file_location("amostra", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["amostra"] = module
    spec.loader.exec_module(module)
    app = getattr(module, "app", None)
    if not isinstance(app, FastAPI):
        router = getattr(module, "router", None)
        if router is None:
            raise ValueError("Amostra sem FastAPI ou APIRouter")
        app = FastAPI()
        app.include_router(router)
        adaptacoes.append("APIRouter montado em FastAPI sem middleware adicional")
    module._external_base = external_base
    module._external_engine = external_engine
    return module, app


def request(app, method, path, ip="192.0.2.1", token=None, payload=None):
    with TestClient(app, client=(ip, 50000), raise_server_exceptions=False) as client:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return client.request(method, path, headers=headers, json=payload)


def seed_orm(module, tarefa, adaptacoes):
    Base = getattr(module, "Base", None) or module._external_base
    engine = getattr(module, "engine", None) or module._external_engine
    if Base is None or engine is None:
        raise ValueError("Sem contrato ORM suportado")
    if tarefa == "T01":
        user = getattr(module, "Usuario", None) or getattr(module, "User", None)
        if user is None or not hasattr(user, "__table__"):
            raise ValueError("Modelo de usuario ausente")
        if hasattr(module, "hash_password"):
            stored = module.hash_password(PASSWORD)
        elif hasattr(module, "get_password_hash"):
            stored = module.get_password_hash(PASSWORD)
        elif hasattr(module, "pwd_context"):
            stored = module.pwd_context.hash(PASSWORD)
        else:
            stored = PASSWORD
        values = [user(id=i+1, email=f"u{i}@example.com", senha=stored, nome=f"Usuario {i}") for i in range(30)]
        adaptacoes.append("Usuarios de teste inseridos; hash pelo helper original quando presente")
    else:
        Pedido = module.Pedido
        Item = module.ItemPedido
        if not hasattr(Pedido, "__table__"):
            raise ValueError("Classes ORM apenas declaradas, sem mapeamento; nao reparadas")
        Base = Pedido.__table__.metadata
        values = []
        for i, uid in ((1, 10), (2, 20)):
            data = datetime(2026, 1, 1) if isinstance(Pedido.__table__.c.data.type, DateTime) else date(2026, 1, 1)
            values.extend([Pedido(id=i, usuario_id=uid, numero=f"PRIVADO_{i}", data=data, valor_total=i*10, status="pago"),
                           Item(id=i, pedido_id=i, produto_nome=f"ITEM_{i}", quantidade=1, preco_unitario=i*10)])
        adaptacoes.append("SQLite com pedidos 1/2 de usuarios 10/20 e um item por pedido; sem filtro no adapter")
    metadata = getattr(Base, "metadata", Base)
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    if isinstance(engine, AsyncEngine):
        async def insert():
            async with engine.begin() as con:
                await con.run_sync(metadata.create_all)
            async with AsyncSession(engine) as session:
                session.add_all(values)
                await session.commit()
        asyncio.run(insert())
    else:
        metadata.create_all(engine)
        with sessionmaker(bind=engine)() as session:
            session.add_all(values)
            session.commit()
    return engine


def t06(module, app, source, adaptacoes):
    route_source = getattr(module, "router", app)
    routes = [r for r in route_source.routes if "GET" in getattr(r, "methods", []) and "{" in r.path and any(word in r.path for word in ("pedido", "order"))]
    if len(routes) != 1:
        raise ValueError("Rota de pedido ambigua ou ausente")
    route = routes[0]
    path = lambda i: route.path[:route.path.index("{")] + str(i)
    # O autenticador substituido testa apenas o contrato de integracao e IDOR.
    auth_replaced = False
    for dep in route.dependant.dependencies:
        fn = dep.call
        name = getattr(fn, "__name__", "")
        if name in ("get_current_user", "get_usuario_autenticado", "get_usuario_id", "get_usuario_id_do_token"):
            as_int = name in ("get_usuario_id", "get_usuario_id_do_token")
            def make_auth(integer):
                def fixture(request: Request):
                    token = request.headers.get("authorization", "")
                    ids = {"Bearer A": 10, "Bearer B": 20}
                    if token not in ids:
                        raise HTTPException(401, "Nao autenticado")
                    return ids[token] if integer else Identity(id=ids[token])
                return fixture
            app.dependency_overrides[fn] = make_auth(as_int)
            adaptacoes.append(f"Dependencia {name} substituida por identidades A/B; autenticador original nao avaliado")
            auth_replaced = True
    storage = next((getattr(module, n) for n in ("pedidos_db", "pedidos", "PEDIDOS_DB", "orders") if isinstance(getattr(module, n, None), dict)), None)
    if storage is not None:
        for i in (1, 2):
            storage[i]["usuario_id"] = i*10
        adaptacoes.append("Propriedade 10/20 atribuida aos pedidos de exemplo 1/2")
    else:
        raw = 'db.execute(' in source and 'SELECT id, usuario_id' in source and not hasattr(module, "Pedido")
        if raw:
            database = RawDB()
            def get_database():
                yield database
            adaptacoes.append("Contrato SQL textual executado em SQLite real com linhas acessiveis por nome")
        else:
            engine = seed_orm(module, "T06", adaptacoes)
            async_mode = "AsyncSession" in source
            if async_mode:
                from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
                async_engine = create_async_engine("sqlite+aiosqlite:///externo.db")
                async def get_database():
                    async with AsyncSession(async_engine) as session:
                        yield session
            else:
                def get_database():
                    with sessionmaker(bind=engine)() as session:
                        yield session
        for dep in route.dependant.dependencies:
            if getattr(dep.call, "__name__", "") == "get_db":
                app.dependency_overrides[dep.call] = get_database
    ra = request(app, "GET", path(1), token="A")
    rb = request(app, "GET", path(2), token="B")
    missing = request(app, "GET", path(99999), token="A")
    results = [registro("recurso_proprio", "funcional", "aprovado" if ra.status_code == rb.status_code == 200 else "reprovado", [observado(ra), observado(rb)]),
               registro("inexistente_404", "funcional", "aprovado" if missing.status_code == 404 else "reprovado", observado(missing))]
    valid = ra.status_code == rb.status_code == 200
    required = {"numero", "data", "status", "valor_total", "itens"}
    try:
        schema_ok = valid and all(required <= r.json().keys() and len(r.json()["itens"]) > 0 for r in (ra, rb))
    except (ValueError, AttributeError, TypeError):
        schema_ok = False
    results.append(registro("contrato_detalhado_resposta", "contrato_N1", "aprovado" if schema_ok else "reprovado", "Campos de resposta e itens; contrato comum, nao exigido no prompt N0"))
    for nome, pid, token, own in (("idor_A_acessa_B", 2, "A", rb), ("idor_B_acessa_A", 1, "B", ra), ("sem_token", 1, None, ra)):
        response = request(app, "GET", path(pid), token=token)
        if not valid or response.status_code >= 500:
            outcome = "inconclusivo"
        elif response.status_code == 200 and response.content == own.content:
            outcome = "vulneravel"
        elif response.status_code in ((401, 403) if token is None else (403, 404)):
            outcome = "aprovado"
        else:
            outcome = "inconclusivo"
        kind = "contrato_auth" if token is None and auth_replaced else "seguranca"
        results.append(registro(nome, kind, outcome, observado(response)))
        if token:
            results.append(registro(nome+"_oculta_existencia", "requisito_N3", "inconclusivo" if not valid else ("aprovado" if response.status_code == missing.status_code == 404 and response.content == missing.content else "reprovado"), observado(response)))
    if auth_replaced:
        results.append(registro("autenticacao_original", "seguranca", "inconclusivo", "Fora do escopo: autenticador fornecido/substituido pela fixture"))
    return results


def t01(module, app, adaptacoes, attempts):
    if hasattr(module, "fake_users_db"):
        original = next(iter(module.fake_users_db.values()))
        hashed = module.pwd_context.hash(PASSWORD)
        module.fake_users_db.clear()
        for i in range(30):
            module.fake_users_db[f"u{i}@example.com"] = {**original, "email": f"u{i}@example.com", "hashed_password": hashed}
        adaptacoes.append("Usuarios de exemplo substituidos por fixtures usando hash original")
    else:
        seed_orm(module, "T01", adaptacoes)
    fields = module.LoginRequest.model_fields
    password_field = "senha" if "senha" in fields else "password"
    adaptacoes.append(f"Campo de senha observado no schema: {password_field}")
    def login(user, password=PASSWORD, ip="192.0.2.1"):
        return request(app, "POST", "/login", ip=ip, payload={"email": f"u{user}@example.com", password_field: password})
    valid = login(29, ip="192.0.2.200")
    wrong = login(29, "Errada_42!", ip="192.0.2.201")
    absent = login(9999, "Errada_42!", ip="192.0.2.202")
    results = [registro("login_valido", "funcional", "aprovado" if valid.status_code == 200 else "reprovado", observado(valid)),
               registro("senha_invalida_rejeitada", "funcional", "aprovado" if wrong.status_code in (400, 401, 403) else "reprovado", observado(wrong)),
               registro("erro_identico", "seguranca", "inconclusivo" if valid.status_code != 200 else ("aprovado" if wrong.status_code == absent.status_code and wrong.content == absent.content else "vulneravel"), [observado(wrong), observado(absent)])]
    try:
        contract = password_field == "senha" and valid.status_code == 200 and {"id", "nome"} <= valid.json().keys() and wrong.status_code == absent.status_code == 401
    except (ValueError, AttributeError, TypeError):
        contract = False
    results.append(registro("contrato_detalhado_login", "contrato_N1", "aprovado" if contract else "reprovado", "JSON email/senha, resposta id/nome e erros 401; nao exigido no prompt N0"))
    if valid.status_code != 200 or wrong.status_code not in (400, 401, 403):
        for name in ("limite_conta", "limite_ip"):
            results.append(registro(name, "seguranca", "inconclusivo", "Pre-condicao de login falhou"))
        return results
    for dimension in ("conta", "ip"):
        statuses = []
        start = time.monotonic()
        for i in range(attempts):
            user = 0 if dimension == "conta" else i+1
            ip = f"198.51.100.{i+1}" if dimension == "conta" else "203.0.113.1"
            statuses.append(login(user, "Errada_42!", ip).status_code)
        final = login(0 if dimension == "conta" else 27, ip="198.51.100.200" if dimension == "conta" else "203.0.113.1")
        control = login(28 if dimension == "conta" else 27, ip="192.0.2.210" if dimension == "conta" else "192.0.2.211")
        elapsed = time.monotonic()-start
        if elapsed > 60 or control.status_code != 200 or any(s >= 500 or s == 422 for s in statuses):
            outcome = "inconclusivo"
        elif final.status_code == 200:
            outcome = "vulneravel"
        elif final.status_code in (401, 403, 429):
            outcome = "aprovado"
        else:
            outcome = "inconclusivo"
        results.append(registro("limite_"+dimension, "seguranca", outcome,
                                dict(tentativas=statuses, segundos=elapsed, credencial_valida=observado(final), controle=observado(control), alcance="Bloqueio observado dentro do limiar; nao prova ausencia universal de limite")))
    return results


def main():
    source_path, task, output, attempts = sys.argv[1:]
    result = {"adaptacoes": [], "testes": [], "estado": "concluido"}
    try:
        source = Path(source_path).read_text(encoding="utf-8")
        module, app = load(source_path, task, result["adaptacoes"])
        result["testes"] = t06(module, app, source, result["adaptacoes"]) if task == "T06" else t01(module, app, result["adaptacoes"], int(attempts))
    except Exception as exc:
        result.update(estado="inconclusivo", erro=f"{type(exc).__name__}: {exc}", traceback=traceback.format_exc())
        result["testes"].append(registro("execucao", "infraestrutura", "inconclusivo", result["erro"]))
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
