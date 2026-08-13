FROM python:3.11-slim

WORKDIR /app

# 安装uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 复制依赖定义
COPY pyproject.toml uv.lock* ./

# 安装依赖
RUN uv sync --frozen --no-dev

# 复制源码
COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
