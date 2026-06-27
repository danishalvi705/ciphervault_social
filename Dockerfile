FROM python:3.12-slim

WORKDIR /app

# Install all system dependencies
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libatspi2.0-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libfreetype6 libfontconfig1 libharfbuzz0b libpng16-16 libx11-6 \
    libxcb1 libxcb-render0 libxrender1 libxext6 libxkbcommon0 \
    gcc g++ make ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium && playwright install-deps

# Copy backgrounds FIRST and verify
COPY backgrounds/ ./backgrounds/
RUN ls -la /app/backgrounds/

# Copy application files
COPY . .

# Verify backgrounds exist
RUN echo "[DOCKER] Contents of /app/backgrounds:" && ls -lah /app/backgrounds/ || echo "[DOCKER] backgrounds folder empty or missing"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
