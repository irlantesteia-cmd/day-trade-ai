FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src

# Instala o pacote com extras de API (fastapi/uvicorn/httpx) e Postgres
RUN pip install --no-cache-dir ".[api,postgres]"

COPY tests/ ./tests
COPY migrations/ ./migrations
COPY alembic.ini ./

EXPOSE 8000

# Entry point: API HTTP (uvicorn)
CMD ["uvicorn", "src.api.http:app", "--host", "0.0.0.0", "--port", "8000"]