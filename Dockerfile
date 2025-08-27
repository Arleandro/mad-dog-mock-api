# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 APP_HOME=/app
WORKDIR ${APP_HOME}
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY docs ./docs
EXPOSE ${PORT}
RUN adduser --disabled-password --gecos "" appuser || true \
 && chown -R 1001:0 ${APP_HOME} || true \
 && chmod -R g+rwX ${APP_HOME} || true
USER 1001
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]
