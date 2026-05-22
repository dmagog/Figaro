FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# каталог для sqlite/clock-state (если контейнер запущен без bind-mount тома)
RUN mkdir -p /app/instance

CMD ["uvicorn", "figaro.web.app:app", "--host", "0.0.0.0", "--port", "8080"]
