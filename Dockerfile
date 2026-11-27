FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/db/library.db

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

RUN groupadd --gid 10001 library \
    && useradd --uid 10001 --gid library --no-create-home library \
    && install -d -o library -g library /data/db

COPY app.py .
COPY templates/ templates/
COPY static/ static/

USER library
EXPOSE 8000
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "app:app"]