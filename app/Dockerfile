FROM figaro-base:latest

WORKDIR /app

ENV PYTHONPATH=/:/app:/worker:/bot

EXPOSE 8080

COPY ./ /app
COPY ./worker /worker
COPY ./bot /bot

CMD ["python", "api.py"]