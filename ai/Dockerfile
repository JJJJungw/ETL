FROM python:3.11-slim

# uv 바이너리만 복사
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Python/uv 동작 관련 환경변수
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/models \
    TRANSFORMERS_CACHE=/models \
    MODEL_CACHE_DIR=/models

# 의존성 레이어 캐시 최적화
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 앱 소스 복사 후 프로젝트까지 설치/동기화
COPY . .
RUN uv sync --frozen

EXPOSE 8001

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]