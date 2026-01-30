FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r bioloupe && useradd -r -g bioloupe bioloupe

COPY src/ /app/src/
COPY alembic/ /app/alembic/
COPY alembic.ini /app/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN chown -R bioloupe:bioloupe /app
USER bioloupe

ENTRYPOINT ["/bin/sh", "-c"]
CMD ["celery -A app.worker.celery_app worker -B --loglevel=info -Q embeddings,indexing,notifications,maintenance -c ${WORKER_CONCURRENCY:-4}"]