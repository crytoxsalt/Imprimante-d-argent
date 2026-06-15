FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg fonts-liberation && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install backend dependencies
COPY web/backend/requirements.txt /tmp/backend-req.txt
RUN pip install --no-cache-dir -r /tmp/backend-req.txt

# Install pipeline dependencies
COPY requirements.txt /tmp/pipeline-req.txt
RUN pip install --no-cache-dir -r /tmp/pipeline-req.txt

# Copy project
COPY . .

ENV PYTHONPATH=/app/src
