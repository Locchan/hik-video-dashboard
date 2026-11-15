FROM python:3.12-alpine

ARG VERSION=dev
ENV HVD_VERSION=${VERSION}

RUN apk add --no-cache \
      build-base \
      libffi-dev \
      openssl-dev \
      cargo \
      curl \
    && pip install --no-cache-dir "poetry>=1.8,<2.2"

# Build context = hik-video-dashboard repo root (with purest submodule).
WORKDIR /src
COPY purest /src/purest
COPY backend /src/backend

WORKDIR /src/backend
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-interaction --no-ansi \
      --extras mysql --extras postgresql \
 && rm -rf /root/.cache

WORKDIR /data
ENV DB_TYPE=sqlite \
    DB_URL=/data/hvd.sqlite \
    REST_PORT=5480 \
    WS_PORT=5481 \
    REST_WORKERS=4 \
    ALERTS_DIR=/alerts

EXPOSE 5480 5481
ENTRYPOINT ["hvd"]
