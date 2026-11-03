"""Instrumento T06 sobre a imagem compartilhada."""
import sys
from v2_instrumento import Instrumento, build, image_id

_i = Instrumento('T06', 10)
run = _i.run

if __name__ == '__main__':
    if '--build' in sys.argv:
        build()
    _i.validar()
