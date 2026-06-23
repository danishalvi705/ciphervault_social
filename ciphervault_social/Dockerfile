# Use the official Playwright image (includes Python and Browser OS dependencies)
FROM mcr.microsoft.com/playwright:v1.40.0-jammy

# 1. Install standard build tools (required for Pillow/Matplotlib/Legacy mode)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    g++ \
    zlib1g-dev \
    libjpeg-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Install the actual Chromium browser binary
RUN playwright install chromium

# 4. Copy your app code
COPY . .

# 5. Run the application
ENV PORT=10000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"]
