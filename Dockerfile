FROM python:3.11-slim

# Install system dependencies including FFmpeg for authorized media processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application source
COPY . .

# Initialize schema and seed demonstration curriculum
RUN mkdir -p instance downloads data \
    && python scripts/init_db.py \
    && python scripts/seed_demo_data.py

EXPOSE 5000

ENV FLASK_ENV=production \
    PORT=5000 \
    PYTHONUNBUFFERED=1

CMD ["gunicorn", "wsgi:app", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120"]
