# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

# Copy requirements first so the dependency layer caches independently of code.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Writable directories for logs and the SQLite database.
RUN mkdir -p logs instance

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# urllib comes from the stdlib - the previous healthcheck imported `requests`,
# which was never installed, so the container was permanently unhealthy.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=5).status == 200 else 1)"

# One eventlet worker: Socket.IO needs WebSocket-capable workers, and multiple
# workers would split clients across processes without a shared message queue.
CMD ["gunicorn", "--worker-class", "eventlet", "--workers", "1", \
     "--bind", "0.0.0.0:5000", "--timeout", "120", \
     "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
