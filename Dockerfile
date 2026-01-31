# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install PyTorch CPU-only version first (much smaller, ~200MB vs ~2.5GB)
# Then install remaining requirements with retries for network reliability
# Use --user to install to /root/.local for later copy
RUN pip install --user --default-timeout=100 --retries 3 \
    torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --user --default-timeout=100 --retries 3 -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r bioloupe && useradd -r -g bioloupe bioloupe

COPY --from=builder /root/.local /home/bioloupe/.local

COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

ENV PATH=/home/bioloupe/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

RUN chown -R bioloupe:bioloupe /app

USER bioloupe

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
