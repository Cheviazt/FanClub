FROM python:3.12-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml ./
COPY bot ./bot
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

FROM python:3.12-slim
RUN useradd -m -u 1000 app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY bot ./bot
COPY assets ./assets
COPY alembic ./alembic
COPY alembic.ini ./
USER app
CMD ["sh", "-c", "alembic upgrade head && python -m bot"]
