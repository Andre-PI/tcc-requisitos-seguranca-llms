FROM python:3.14.2-slim@sha256:1a3c6dbfd2173971abba880c3cc2ec4643690901f6ad6742d0827bae6cefc925
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/runner
COPY requirements.txt /runner/requirements.txt
RUN python -m pip install --no-cache-dir -r /runner/requirements.txt
COPY t03_verificador.py t03_referencias.py t03_worker_linux.py /runner/
USER 10001:10001
WORKDIR /tmp
ENTRYPOINT ["python", "/runner/t03_worker_linux.py"]
