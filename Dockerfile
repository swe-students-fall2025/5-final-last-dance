FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY Pipfile Pipfile.lock ./

RUN pip install --no-cache-dir pipenv && \
    pipenv install --deploy --ignore-pipfile

COPY . .

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000')" || exit 1

CMD ["pipenv", "run", "flask", "run", "--host", "0.0.0.0"]
