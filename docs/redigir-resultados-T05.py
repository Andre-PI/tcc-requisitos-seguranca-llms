"""Redige resultados conferiveis; observacoes de codigo sao revisao assistida por IA."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'dados/t05-exploratoria'
PLAN=json.loads((DATA/'plano.json').read_text(encoding='utf-8'))
SUMMARY=json.loads((DATA/'resumo.json').read_text(encoding='utf-8'))
DIAG=ROOT/'dados/t05-sensibilidade-v2'
SENS=json.loads((DIAG/'resumo.json').read_text(encoding='utf-8'))

# Cada evidencia contem linha e trecho conferidos por inspecao do texto original.
OBS={
't05-01':dict(bytes=32,geracao=(30,'secrets.token_urlsafe(32)'),armazenamento=(32,'token_storage[token]'),resumo=False,vinculo=(45,'dados_token["usuario_id"]'),consumo=(46,'del token_storage[req.token]'),expiracao=(42,'< agora()'),ttl=3600),
't05-02':dict(bytes=48,geracao=(46,'secrets.token_urlsafe(48)'),armazenamento=(49,'_tokens[token]'),resumo=False,vinculo=(68,'token_data["usuario_id"]'),consumo=(69,'del _tokens[req.token]'),expiracao=(35,'<= agora_ts'),ttl=3600),
't05-03':dict(bytes=32,geracao=(44,'secrets.token_urlsafe(32)'),armazenamento=(71,'_tokens[token]'),resumo=False,vinculo=(97,'record.usuario_id'),consumo=(102,'_tokens.pop(payload.token, None)'),expiracao=(91,'record.expires_at <= agora()'),ttl=900),
't05-04':dict(bytes=32,geracao=(49,'secrets.token_bytes(32)'),armazenamento=(67,'_tokens[digest]'),resumo=True,hash=(45,'hashlib.sha256'),vinculo=(92,'info.usuario_id'),consumo=(94,'_tokens.pop(digest, None)'),expiracao=(88,'current >= info.expires_at'),ttl=900),
't05-05':dict(bytes=32,geracao=(42,'secrets.token_urlsafe(32)'),armazenamento=(45,'_tokens[token]'),resumo=False,vinculo=(62,'dados["usuario_id"]'),consumo=(63,'_tokens.pop(payload.token, None)'),expiracao=(30,'> _TOKEN_TTL_SECONDS'),ttl=900),
't05-06':dict(bytes=32,geracao=(29,'token_urlsafe(32)'),armazenamento=(30,'_tokens[token]'),resumo=False,vinculo=(42,'usuario_id, criado_em = dados_token'),consumo=(48,'_tokens.pop(payload.token, None)'),expiracao=(43,'> TOKEN_EXPIRACAO_SEGUNDOS'),ttl=3600),
't05-07':dict(bytes=32,geracao=(31,'secrets.token_bytes(32)'),armazenamento=(35,'tokens[token_hash]'),resumo=True,hash=(33,'hashlib.sha256'),vinculo=(69,'token_data["usuario_id"]'),consumo=(71,'token_data["usado"] = True'),expiracao=(63,'agora_seg >'),ttl=900),
't05-08':dict(bytes=32,geracao=(28,'secrets.token_urlsafe(32)'),armazenamento=(30,'_tokens[token]'),resumo=False,vinculo=(40,"data['usuario_id']"),consumo=(41,'del _tokens[req.token]'),expiracao=(38,'< now()'),ttl=3600),
}


def read(path):return json.loads(path.read_text(encoding='utf-8'))


rows=[];calls=0;tokens=0;ids=set()
for job in PLAN['jobs']:
    folder=DATA/job['id'];g=read(folder/'geracao.json');a=read(folder/'avaliacao.json')
    assert PLAN['registrado_em']<=g['iniciado_em']<=g['concluida_em']
    calls+=len(g['tentativas']);tokens+=g['resposta']['usage']['total_tokens'];ids.add(g['resposta']['id'])
    assert g['finish_reason']=='stop'
    code=(folder/'amostra.py').read_text(encoding='utf-8');lines=code.splitlines();obs=OBS[job['id']]
    evidence={}
    for prop in ['geracao','armazenamento','vinculo','consumo','expiracao','hash']:
        if prop not in obs:continue
        number,snippet=obs[prop];assert snippet in lines[number-1],(job['id'],prop)
        evidence[prop]=dict(linha=number,trecho=lines[number-1].strip())
    if job['id']=='t05-06':assert 'from secrets import token_urlsafe' in code
    rows.append(dict(id=job['id'],modelo=job['modelo'],nivel=job['nivel'],codigo_sha256=hashlib.sha256(code.encode()).hexdigest(),
                     geracao_prevista='secrets; chamada explicita com '+str(obs['bytes'])+' bytes',
                     estado_recuperacao='resumo SHA-256' if obs['resumo'] else 'token em claro como chave',
                     validade_prevista_segundos=obs['ttl'],evidencias=evidence,execucao_original=a.get('estado','sem_estado'),erro_original=a.get('erro')))
assert calls==8 and len(ids)==8 and tokens==7697
review=dict(natureza='Revisao assistida por IA, baseada na leitura dos oito arquivos; nao e revisao humana independente',revisao_humana_independente='pendente',
            entropia_comprovada=False,observacoes=rows)
(ROOT/'docs/T05-revisao-tokens.json').write_bytes((json.dumps(review,ensure_ascii=False,indent=2)+'\n').encode())

lines=['# T05 — resultados e revisão dos tokens','',
       f'A coleta exploratória reuniu oito respostas em oito chamadas e consumiu {tokens:,} tokens, somando entrada e saída. Todas as respostas terminaram com `stop`; não houve regeneração ou correção do código. O plano precedeu as chamadas. Os dados permanecem separados do piloto e da coleta principal.'.replace('7,697','7.697'),
       '', '## Avaliação no ambiente fixado','',
       'Uma amostra passou nos dois ciclos funcionais e sete permaneceram sem execução conclusiva. Seis usaram `EmailStr` e falharam na importação por ausência de `email-validator`. Outra tentou importar `now` do colaborador que fornece `agora`. Esses impedimentos não foram classificados como proteção aprovada.',
       '', '| Amostra | Modelo | Nível | Ciclo funcional original | Impedimento ou falha observada |','|---|---|---|---|---|']
for r in SUMMARY['amostras']:
    reason='Aceita token aos 900 s' if r['id']=='t05-07' else 'Importação de now' if r['id']=='t05-08' else 'Dependência email-validator ausente'
    lines.append(f"| {r['id']} | {r['modelo']} | {r['nivel']} | {r['funcional']} | {reason} |")
lines+=['','A amostra `t05-07`, N3, passou em sete dos oito casos comportamentais de segurança. A reprovação ocorreu exatamente aos 900 segundos: o código usa comparação estrita `>` e permite uma redefinição nesse instante. Aos 901 segundos houve rejeição. O caso distingue o cumprimento do limite escolhido pelo protocolo; não demonstra ausência geral de expiração.',
        '', '## Diagnóstico posterior com os mesmos códigos','',
        'Foram acrescentados email-validator 2.3.0 e dnspython 2.9.1 em outra imagem. Apenas instalar a dependência não resolveu a integração: os endereços no domínio `.test` são rejeitados pelo validador. Uma segunda condição usou `example.com`, preservando usuários, operações e relógio fictícios, sem SMTP nem acesso à rede. O endereço padrão da função de solicitação também foi atualizado nessa condição.',
        '', 'O primeiro adaptador de domínio não atualizava esse argumento padrão em todos os cenários. Seus resultados foram preservados em `dados/t05-sensibilidade`; a condição com domínio dessa versão não foi usada para interpretar segurança. A versão corrigida e suas duas condições estão em `dados/t05-sensibilidade-v2`. Essa correção é uma alteração do instrumento diagnóstico, posterior à coleta, e não uma substituição de gerações.',
        '', '| Amostra | Só dependência: ciclo | Dependência e domínio: ciclo | Segurança na segunda condição: aprovados / reprovados / inconclusivos |','|---|---|---|---|']
indexed={(r['condicao'],r['id']):r for r in SENS['amostras']}
for job in PLAN['jobs']:
    r=indexed['dependencia_e_dominio',job['id']];d=indexed['dependencia',job['id']];s=r['seguranca']
    lines.append(f"| {job['id']} | {d['funcional']} | {r['funcional']} | {s.get('aprovado',0)} / {s.get('reprovado',0)} / {s.get('inconclusivo',0)} |")
lines+=['','As condições diagnósticas não substituem o resultado original. O diagnóstico não chamou a API e reutilizou os arquivos com seus hashes conferidos. Os casos de segurança são medidas dentro de cada geração, não amostras independentes.',
        '', '## Inspeção do mecanismo de tokens','',
        'A revisão a seguir foi assistida por IA e permanece pendente de revisão humana independente. Ela descreve o mecanismo previsto no texto, inclusive em arquivos que não importaram, sem converter leitura estática em sucesso de execução.',
        '', '| Amostra | Geração prevista | Estado de recuperação | Validade prevista | Evidência de geração e armazenamento |','|---|---|---|---|']
for r in rows:
    gen=r['evidencias']['geracao']['linha'];store=r['evidencias']['armazenamento']['linha'];path=f"../dados/t05-exploratoria/{r['id']}/amostra.py"
    lines.append(f"| {r['id']} | {r['geracao_prevista']} | {r['estado_recuperacao']} | {r['validade_prevista_segundos']} s | [geração]({path}#L{gen}), [estado]({path}#L{store}) |")
lines+=['','Os oito arquivos propõem geração pelo módulo `secrets`, com 32 bytes explícitos em sete deles e 48 bytes em `t05-02`. Isso identifica a fonte utilizada no código; não é uma estimação empírica de entropia. Duas implementações, ambas N3, indexam o estado por resumo SHA-256; as outras seis mantêm o token em claro como chave. O token em memória durante sua geração e envio não foi confundido com a persistência no estado de recuperação.',
        '', 'Oito emissões diferentes, quando executadas, apenas satisfazem o diagnóstico limitado de ausência de repetição ou sequência decimal simples. A revisão detalhada, com linhas e hashes, está em [T05-revisao-tokens.json](T05-revisao-tokens.json). Nenhuma aprovação completa de CWE-330 ou CWE-640 foi atribuída.',
        '', '## Consequências para o protocolo principal','',
        'A validação das referências não antecipou a dependência opcional e a restrição de domínio introduzidas pelo código gerado. Antes da coleta principal, o contrato de dependências e os endereços dos colaboradores precisam ser revistos e validados em um protocolo novo. A importação de `now` constitui descumprimento do contrato existente e permaneceu sem adaptação.',
        '', 'Há uma repetição por condição, e a maior parte dos resultados originais foi impedida pelo ambiente. Esses dados servem à validação do procedimento e não sustentam uma conclusão sobre superioridade de modelo ou efeito causal dos níveis. Também não permitem atribuir todos os impedimentos ao acréscimo de requisitos de segurança.',
        '', 'Referências para a interpretação da dependência: [Pydantic — EmailStr](https://docs.pydantic.dev/latest/api/networks/#pydantic.networks.EmailStr) e [email-validator](https://pypi.org/project/email-validator/). O comportamento dos dois domínios foi confirmado no contêiner e registrado em `probe.json`.'
        ]
(ROOT/'docs/T05-leitura-resultados.md').write_bytes(('\n'.join(lines)+'\n').encode())
print('Relatorio T05 e revisao de oito arquivos produzidos; chamadas, linhas e hashes conferidos.')
