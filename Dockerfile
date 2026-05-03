FROM python:3.11-slim

WORKDIR /app

# System dependencies for network/SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source code
COPY src/ src/
# .env is mounted at runtime

# Environment
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1

# Default: run the daily pipeline
CMD ["python3", "src/run_daily.py"]
