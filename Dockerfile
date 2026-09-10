# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home app \
    && mkdir -p /home/app/.EasyOCR \
    && chown -R app:app /home/app

COPY pyproject.toml ./
RUN pip install --no-cache-dir torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

COPY . .
RUN pip install --no-cache-dir '.[ocr]' \
    && chown -R app:app /app

USER app
ENV HOME=/home/app
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
