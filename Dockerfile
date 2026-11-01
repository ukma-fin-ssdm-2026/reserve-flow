FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN 'pip install --only-binary :all: --no-cache-dir -r requirements.txt'

COPY src/ ./src/
COPY docs/ ./docs/

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 3000

CMD ["sh", "-c", "python src/api/seed.py && uvicorn main:app --app-dir src/api --host 0.0.0.0 --port ${PORT:-3000}"]

#Використання ШІ: згенеровано за допомогою ШІ Gemini, перевірено та затверджено командою.
