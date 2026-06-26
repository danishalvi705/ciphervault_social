# 1. Use the official Playwright Python image
FROM mcr.microsoft.com/playwright/python:v1.60.0-jammy

# 2. Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    g++ \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. Install Python dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# 4. CRITICAL: Explicitly install browser binaries and dependencies
# This ensures Chromium and all required system libraries (libgbm, libnss3, etc.)
# are linked correctly in the container environment.
RUN playwright install chromium
RUN playwright install-deps

# 5. Copy your app code
COPY . .

# 6. Run the application
ENV PORT=10000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
