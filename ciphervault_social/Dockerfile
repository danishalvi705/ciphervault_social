FROM python:3.12-slim

# ffmpeg is required by MoviePy for video encoding; not present in the
# slim base image and not installable via pip.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    zlib1g-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render injects $PORT at runtime; default to 10000 for local testing.
ENV PORT=10000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
