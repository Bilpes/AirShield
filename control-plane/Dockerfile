FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7 AS builder
WORKDIR /build
RUN python -m venv /venv
ENV PATH=/venv/bin:$PATH
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
ARG SPACY_MODEL_URL=https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
ARG SPACY_MODEL_SHA256=1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85
RUN python -c "import urllib.request; urllib.request.urlretrieve('${SPACY_MODEL_URL}', '/tmp/model.whl')" \
    && echo "${SPACY_MODEL_SHA256}  /tmp/model.whl" | sha256sum -c - \
    && pip install --no-cache-dir /tmp/model.whl \
    && rm /tmp/model.whl

FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7
RUN groupadd --system --gid 10001 airshield \
    && useradd --system --uid 10001 --gid airshield --home /nonexistent airshield \
    && apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /service
COPY --from=builder /venv /venv
COPY app ./app
COPY policies ./policies
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
ENV PATH=/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    POLICY_DIRECTORY=/service/policies
USER 10001:10001
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-proxy-headers"]
