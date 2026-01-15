FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for lxml or mysqlclient)
# gcc and pkg-config might be needed for some python libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]

