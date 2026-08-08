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
RUN pip install --no-cache-dir -e ".[dev]"

ENV MOMENTUM_DB=/data/momentum.db
ENV MOMENTUM_DATA_DIR=/data
ENV MOMENTUM_LOG_LEVEL=INFO
ENV MOMENTUM_SIMULATION_MODE=true
ENV MOMENTUM_API_HOST=0.0.0.0

VOLUME ["/data"]

EXPOSE 8000

CMD ["python", "-m", "momentum", "simulate", "--days", "7"]
