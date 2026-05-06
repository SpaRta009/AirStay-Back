FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    gdal-bin \
    libgdal-dev \
    python3-dev \
    libffi-dev \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install GDAL==$(gdal-config --version)

COPY . .

EXPOSE 8000

# Après
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn AirBNB.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]