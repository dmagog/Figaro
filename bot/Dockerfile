FROM python:3.10-slim

WORKDIR /

COPY ./bot /bot
COPY ./app /app

ENV PYTHONPATH=/:/app:/worker:/bot

RUN pip install aiogram==2.25.2 python-dotenv sqlmodel psycopg2-binary pydantic-settings pandas

CMD ["python", "/bot/bot.py"] 