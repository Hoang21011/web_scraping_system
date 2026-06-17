FROM python:3.11-slim AS web_scraping_system
WORKDIR /build/web_scraping

RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --default-timeout=1000 --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app

COPY hybrid_method/         ./hybrid_method

COPY --from=web_scraping_system /install /usr/local
EXPOSE 8000
ENV PORT=8000
ENV PYTHONPATH=/app

# Khởi chạy Jupyter Lab ở port 8000 để Healthcheck pass và bạn có thể truy cập Notebook
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8000", "--no-browser", "--allow-root", "--ServerApp.token=''", "--ServerApp.password=''"]
