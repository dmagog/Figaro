FROM figaro-base:latest

WORKDIR /

ENV PYTHONPATH=/:/app:/worker:/bot

COPY ./bot /bot
COPY ./app /app

CMD ["python", "/bot/bot.py"] 