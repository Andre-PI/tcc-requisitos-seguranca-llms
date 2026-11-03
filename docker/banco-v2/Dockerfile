FROM python:3.14.2-slim@sha256:1a3c6dbfd2173971abba880c3cc2ec4643690901f6ad6742d0827bae6cefc925
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/runner TCC_BANCO_ISOLADO=1
COPY requirements.txt /runner/requirements.txt
RUN python -m pip install --no-cache-dir -r /runner/requirements.txt
COPY v2_banco.py v2_worker_linux.py t01_verificador.py t01_referencias.py t02_verificador.py t02_referencias.py t06_verificador.py t06_referencias.py /runner/
USER 10001:10001
WORKDIR /tmp
ENTRYPOINT ["python", "/runner/v2_worker_linux.py"]
