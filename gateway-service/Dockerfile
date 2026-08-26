FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/airshield

RUN groupadd --system --gid 10002 airshield \
    && useradd --system --uid 10002 --gid 10002 --create-home --home-dir /home/airshield airshield

WORKDIR /app
COPY pyproject.toml /app/pyproject.toml
COPY app /app/app
RUN pip install --upgrade "pip==26.0.1" \
    && pip install . \
    && chown -R 10002:10002 /app /home/airshield

USER 10002:10002
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-proxy-headers"]
