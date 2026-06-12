FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UPGRADE_COPILOT_HOST=0.0.0.0 \
    UPGRADE_COPILOT_PORT=8000 \
    UPGRADE_COPILOT_INDEX_PATH=/app/data/index.json \
    UPGRADE_COPILOT_CACHE_DIR=/app/data/cache \
    UPGRADE_COPILOT_REPO_ROOT=/workspace

WORKDIR /app

RUN addgroup --system --gid 10001 app \
    && adduser --system --uid 10001 --ingroup app app

COPY pyproject.toml README.md ./
COPY src ./src
COPY data/official_sources.json ./data/official_sources.json
COPY data/index.json ./data/index.json
COPY data/cache ./data/cache

RUN mkdir -p /workspace /app/data/cache \
    && chown -R app:app /app /workspace

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import json, urllib.request; json.load(urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2))['ready']"

CMD ["python", "-m", "upgrade_copilot.cli", "serve"]
