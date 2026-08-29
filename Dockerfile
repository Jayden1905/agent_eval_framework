# One image for backend + agents — mirrors backend/server.py, which serves
# both from a single uvicorn process ("One Python process serves everything",
# see README.md). Build/run with docker-compose.yml, not `docker run` directly
# (secrets come from .env via env_file, not baked into the image).
FROM python:3.13-slim

WORKDIR /app

# Layer-cache the dependency install separately from source so editing
# backend/*.py or agents/*.py doesn't invalidate the pip layer.
# requirements.txt stays the single source of truth (still what `make
# install` uses) — streamlit is in there only for hack.py's Streamlit
# fallback, which isn't part of this image (not COPYed below), so it's
# filtered out here at build time rather than hand-duplicated into a
# second requirements file that could drift.
COPY requirements.txt .
RUN grep -v '^streamlit' requirements.txt > requirements.docker.txt \
    && pip install --no-cache-dir -r requirements.docker.txt

# Only what backend/server.py needs at runtime: the FastAPI app + the
# three mounted demo agents. frontend/, scripts/, docs/, hack.py etc. are
# excluded via .dockerignore — they're not imported by backend.server.
COPY backend/ backend/
COPY agents/ agents/

EXPOSE 8000

# `make dev`'s command, minus --reload (no source watching in a container)
# and with --host 0.0.0.0 (Makefile's default 127.0.0.1 bind is unreachable
# from outside the container). USE_MOCKS is read at import time by
# backend/server.py, so `docker compose run -e USE_MOCKS=1` / `make
# docker-mocks` switches modes without changing this file.
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "8000"]
