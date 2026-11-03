FROM tcc-t05:validacao-1
USER root
COPY requirements.txt /runner/sensibilidade-requirements.txt
RUN python -m pip install --no-cache-dir --no-deps -r /runner/sensibilidade-requirements.txt
COPY t05_sensibilidade_worker.py /runner/
USER 10001:10001
ENTRYPOINT ["python", "/runner/t05_sensibilidade_worker.py"]
