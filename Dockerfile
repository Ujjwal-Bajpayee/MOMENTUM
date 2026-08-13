FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY momentum/ ./momentum/

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir .

ENV MOMENTUM_DB=/data/momentum.db
ENV MOMENTUM_DATA_DIR=/data
ENV MOMENTUM_LLM_PROVIDER=ollama
ENV MOMENTUM_LLM_MODEL=deepseek-r1:8b

VOLUME ["/data"]

ENTRYPOINT ["python", "-m", "momentum"]
CMD ["--help"]
