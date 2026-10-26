FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    INPUT_PATH=/app/data/sample \
    PROCESSED_PATH=/app/data/processed \
    REJECTED_PATH=/app/data/rejected \
    STORAGE_BACKEND=local

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 app

COPY src ./src
COPY data/sample ./data/sample
RUN mkdir -p /app/data/processed /app/data/rejected \
    && chown -R app:app /app/data

USER app
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--input", "/app/data/sample"]
