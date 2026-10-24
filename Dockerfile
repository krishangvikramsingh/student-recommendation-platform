FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    SRP_HOST=0.0.0.0 SRP_PORT=8000 SRP_DB_PATH=/data/platform.db \
    SRP_OUTBOX_PATH=/data/outbox.log SRP_BASE_URL=http://localhost:8000
RUN useradd --system --uid 10001 --home /app srp && mkdir /data && chown srp /data
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
USER srp
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["python", "-m", "srp"]
