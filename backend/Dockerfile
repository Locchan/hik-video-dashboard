FROM python:3.12-alpine

ARG VERSION=dev
ENV HVD_VERSION=${VERSION}

# No apk build toolchain (build-base/cargo/dev headers). Runtime deps are
# purest (stdlib scrypt) + SQLAlchemy / psycopg2-binary / Pillow wheels.
RUN pip install --no-cache-dir "poetry>=1.8,<2.2"

# Build context = hik-video-dashboard repo root (with purest submodule).
WORKDIR /src
COPY purest /src/purest
COPY backend /src/backend
# Independent frontend semver for GET /version (overridable via HVD_FRONTEND_VERSION).
COPY frontend/VERSION /usr/local/share/hvd/FRONTEND_VERSION

WORKDIR /src/backend
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-interaction --no-ansi \
      --extras postgresql \
 && rm -rf /root/.cache

WORKDIR /data
ENV DB_TYPE=postgresql \
    REST_PORT=5480 \
    WS_PORT=5481 \
    REST_WORKERS=4 \
    ALERTS_DIR=/alerts

EXPOSE 5480 5481
ENTRYPOINT ["hvd"]
