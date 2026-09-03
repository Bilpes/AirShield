FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

RUN groupadd --system --gid 10001 airshield \
    && useradd --system --uid 10001 --gid airshield --home /nonexistent airshield \
    && apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libsndfile1 libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /service

COPY requirements.txt ./

ARG SPACY_MODEL_URL=https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
ARG SPACY_MODEL_SHA256=1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85

RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "import urllib.request; urllib.request.urlretrieve('${SPACY_MODEL_URL}', '/tmp/en_core_web_sm-3.8.0-py3-none-any.whl')" \
    && echo "${SPACY_MODEL_SHA256}  /tmp/en_core_web_sm-3.8.0-py3-none-any.whl" | sha256sum -c - \
    && pip install --no-cache-dir /tmp/en_core_web_sm-3.8.0-py3-none-any.whl \
    && rm /tmp/en_core_web_sm-3.8.0-py3-none-any.whl

COPY --chown=10001:10001 app ./app

RUN mkdir -p /models && chown 10001:10001 /models

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/models/huggingface \
    XDG_CACHE_HOME=/models/cache

USER 10001:10001

EXPOSE 8001

HEALTHCHECK --interval=20s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/v1/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--no-proxy-headers"]