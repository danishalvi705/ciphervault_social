FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libfreetype6 libfontconfig1 libharfbuzz0b libpng16-16 libx11-6 \
    libxcb1 libxcb-render0 libxrender1 libxext6 libxkbcommon0 \
    gcc g++ make && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
