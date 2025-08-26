FROM python:3.12-slim

# Install ClamAV and download the latest virus definitions
RUN apt-get update && apt-get install -y clamav --no-install-recommends && \
    rm -rf /var/lib/apt/lists/* && \
    echo "Downloading initial ClamAV definitions..." && \
    freshclam

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
