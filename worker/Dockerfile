FROM figaro-base:latest

WORKDIR /

ENV PYTHONPATH=/:/app:/worker:/bot

COPY ./worker /worker
COPY ./bot /bot
COPY ./app /app

CMD ["celery", "-A", "worker.celery_worker", "worker", "--loglevel=info"] 