# Use python 3.12 slim
FROM python:3.12-slim

# Set environment variables to optimize Python for container usage
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies including FFmpeg and Playwright requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 libasound2 libfreetype6 \
    libfontconfig1 libharfbuzz0b libpng16-16 libx11-6 libxcb1 \
    libxcb-render0 libxrender1 libxext6 libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (System dependencies for browser included above)
RUN playwright install chromium && playwright install-deps

# Create directories and copy source code
RUN mkdir -p /app/backgrounds
COPY backgrounds/ ./backgrounds/
COPY . .

# Verification step (keeps the logs informative)
RUN echo "[DOCKER] Verified /app/backgrounds contents:" && ls -lah /app/backgrounds/

EXPOSE 8000

# Start command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
