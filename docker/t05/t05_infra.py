"""Colaboradores ficticios T05: sem SMTP, banco real ou credenciais reais."""
import types

A='alice@example.test'
B='bruno@example.test'
UNKNOWN='ausente@example.test'
NEW='T05-nova-senha-ficticia-A!'
OTHER='T05-outra-senha-ficticia-B!'


def criar_infra():
    m=types.ModuleType('tcc_t05_infra')
    m.usuarios={A:{'id':1,'email':A},B:{'id':2,'email':B}}
    # Apenas estado sintetico do colaborador, nunca armazenamento de producao.
    m.senhas={1:'T05-antiga-A-ficticia!',2:'T05-antiga-B-ficticia!'}
    m.envios=[];m.alteracoes=[];m.tempo=1700000000.0
    def usuario_por_email(email):
        user=m.usuarios.get(email)
        return dict(user) if user else None
    def definir_senha(usuario_id,nova_senha):
        if usuario_id not in m.senhas:raise KeyError('Usuario de teste inexistente')
        m.alteracoes.append({'usuario_id':usuario_id})
        m.senhas[usuario_id]=nova_senha
    def enviar_email(email,token):m.envios.append({'email':email,'token':token})
    m.usuario_por_email=usuario_por_email;m.definir_senha=definir_senha;m.enviar_email=enviar_email;m.agora=lambda:m.tempo
    return m
