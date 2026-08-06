FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    OPEN_BROWSER=0 \
    HOST=0.0.0.0 \
    PORT=8765 \
    CTH_PYTHON_BIN=/usr/local/bin/python \
    CTH_ALLOW_SYSTEM_PYTHON=true

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-prod.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements-prod.txt
COPY . .
RUN chmod +x start_prod.sh \
    && mkdir -p /app/instance \
    && test -x "$CTH_PYTHON_BIN" \
    && "$CTH_PYTHON_BIN" --version \
    && "$CTH_PYTHON_BIN" -c "import fastapi, sqlalchemy, psycopg, boto3"
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD curl -fsS "http://127.0.0.1:${PORT:-8765}/api/health" || exit 1
CMD ["./start_prod.sh"]
