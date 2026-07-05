FROM python:3.11-slim

WORKDIR /app

# Install FFmpeg and system deps for Playwright
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and dependencies
RUN playwright install && \
    playwright install-deps

# Copy app
COPY . .

# Create backgrounds dir
RUN mkdir -p backgrounds

# Run
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
