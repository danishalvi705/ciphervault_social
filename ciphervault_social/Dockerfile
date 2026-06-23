# 1. Use the official Playwright Python image (includes Python and Browsers)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 2. Install system dependencies for your legacy rendering (ffmpeg, etc.)
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
# Using "python -m pip" is the safest way to ensure the correct environment is used
RUN python -m pip install --no-cache-dir -r requirements.txt

# 4. Copy your app code
COPY . .

# 5. Run the application
ENV PORT=10000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
