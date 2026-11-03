FROM python:3.12.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# приложение не работает от root
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

# сначала зависимости (версии зафиксированы в requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# в образ попадает только код приложения
COPY --chown=app:app app ./app
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app static ./static
COPY --chown=app:app alembic.ini .

USER app

EXPOSE 8000

# сигнал остановки
STOPSIGNAL SIGTERM
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
