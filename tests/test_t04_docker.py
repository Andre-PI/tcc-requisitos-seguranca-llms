from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from t04_docker import command


def test_comando_nao_monta_repositorio_ou_socket_e_limita_recursos(tmp_path):
    source=tmp_path/'amostra.py';source.write_text('app=None')
    cmd=command('sha256:imagem-fixada','tcc-t04-000000000000',['--amostra','/candidate/amostra.py'],source)
    assert '--network=none' in cmd
    assert '--read-only' in cmd and '--cap-drop=ALL' in cmd
    assert '--security-opt=no-new-privileges=true' in cmd
    assert cmd[cmd.index('--user')+1]=='10001:10001'
    assert '--memory=512m' in cmd and '--pids-limit=64' in cmd
    assert cmd.count('--mount')==1
    mount=cmd[cmd.index('--mount')+1]
    assert mount.endswith('target=/candidate/amostra.py,readonly')
    assert 'docker.sock' not in ' '.join(cmd)
    assert 'OPENAI_API_KEY' not in ' '.join(cmd)
    assert cmd[-3:]==['sha256:imagem-fixada','--amostra','/candidate/amostra.py']
