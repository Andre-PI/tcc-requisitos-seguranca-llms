"""Aplicações locais de referência. As variantes falhas são controles de teste."""
import io
from pathlib import Path
import uuid
from PIL import Image,UnidentifiedImageError
from fastapi import FastAPI,UploadFile,File,HTTPException
from t03_verificador import MAX_BYTES,MAX_SIDE

MODOS=('protegida','vulneravel','nega_tudo','finge_sucesso','so_cabecalho','grava_antes','colide_nome','sem_limite','sem_dimensao')


def criar_app(base,modo):
    base=Path(base).resolve()
    if modo not in MODOS:raise ValueError(modo)
    app=FastAPI()
    @app.post('/foto',status_code=201)
    async def upload(arquivo:UploadFile=File(...)):
        if modo=='nega_tudo':raise HTTPException(415,'Arquivo invalido')
        if modo=='finge_sucesso':return {'arquivo':'fantasma.png'}
        data=await arquivo.read()
        if modo=='vulneravel':
            target=base/(arquivo.filename or 'foto.png')
            target.write_bytes(data)
            return {'arquivo':target.name}
        if modo=='so_cabecalho':
            if arquivo.content_type not in ('image/png','image/jpeg') or Path(arquivo.filename or '').suffix.lower() not in ('.png','.jpg','.jpeg'):
                raise HTTPException(415,'Arquivo invalido')
            target=base/(uuid.uuid4().hex+'.png');target.write_bytes(data)
            return {'arquivo':target.name}
        temp=None
        if modo=='grava_antes':
            temp=base/(uuid.uuid4().hex+'.tmp');temp.write_bytes(data)
        try:
            if modo!='sem_limite' and len(data)>MAX_BYTES:raise HTTPException(413,'Arquivo excede limite')
            if not data or Path(arquivo.filename or '').suffix.lower() not in ('.png','.jpg','.jpeg'):
                raise HTTPException(415,'Arquivo invalido')
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('PNG','JPEG'):raise HTTPException(415,'Arquivo invalido')
                if modo!='sem_dimensao' and (image.width>MAX_SIDE or image.height>MAX_SIDE):raise HTTPException(400,'Dimensoes invalidas')
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load();out=io.BytesIO();image.convert('RGB').save(out,format='PNG')
            name='perfil.png' if modo=='colide_nome' else uuid.uuid4().hex+'.png'
            (base/name).write_bytes(out.getvalue())
            return {'arquivo':name}
        except (UnidentifiedImageError,OSError,ValueError):raise HTTPException(415,'Arquivo invalido')
        finally:
            if temp is not None:temp.unlink(missing_ok=True)
    return app
