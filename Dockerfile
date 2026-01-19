# Dockerfile
FROM python:3.10-slim

# Variables d'environnement pour Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dépendances système
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

# Répertoire de travail
WORKDIR /app

# Copier requirements et installer
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copier le projet
COPY . .

# Collecte des statics
RUN python manage.py collectstatic --noinput

# Port exposé
EXPOSE 8000

# Commande de lancement
CMD ["gunicorn", "AirBNB.wsgi:application", "--bind", "0.0.0.0:8000"]
