FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app

RUN mkdir -p /app/data/db \
    /app/data/documents/raw \
    /app/data/documents/parsed \
    /app/data/documents/index

EXPOSE 8000

CMD ["python", "-m", "app.main"]
