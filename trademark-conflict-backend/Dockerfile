FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \

    && apt-get install -y --no-install-recommends \

        libglib2.0-0 \

        libgl1 \

        libsm6 \
        libxext6 \
        libxrender1 \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-mya \

    && rm -rf /var/lib/apt/lists/*

COPY requirements-production.txt .

RUN pip install --no-cache-dir \

    -r requirements-production.txt

COPY app ./app
COPY apexive_mcp ./apexive_mcp
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

RUN mkdir -p \

    /app/uploads \

    /app/extracted \

    /app/evidence

EXPOSE 8000

EXPOSE 8100

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]