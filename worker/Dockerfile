FROM python:3.10-slim

WORKDIR /

COPY ./worker /worker
COPY ./bot /bot
COPY ./app /app

ENV PYTHONPATH=/:/app:/worker:/bot

RUN pip install celery aiogram==2.25.2 python-dotenv sqlmodel psycopg2-binary pandas

CMD ["celery", "-A", "worker.celery_worker", "worker", "--loglevel=info"] 