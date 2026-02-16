FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim
WORKDIR /app
ENV UV_SYSTEM_PYTHON=1
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]