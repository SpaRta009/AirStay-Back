from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# === GeoDjango / GDAL Setup (Windows local uniquement) ===
import sys
import ctypes

if sys.platform == "win32":
    GDAL_DLL_PATH = r"D:\AirBNB\.venv\Lib\site-packages\osgeo\gdal304.dll"
    if os.path.exists(GDAL_DLL_PATH):
        ctypes.CDLL(GDAL_DLL_PATH)
        GDAL_LIBRARY_PATH = GDAL_DLL_PATH

# =====================
# Sécurité
# =====================
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# =====================
# Applications
# =====================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    "corsheaders",
    "rest_framework.authtoken",
    'django_cleanup.apps.CleanupConfig',
    'rest_framework',
    'rest_framework_gis',
    'backEnd',
]

# =====================
# Middleware
# =====================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',       # ← doit être en 2e
    'corsheaders.middleware.CorsMiddleware',            # ← avant CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'AirBNB.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'AirBNB.wsgi.application'

# =====================
# Base de données
# =====================
if os.environ.get('DATABASE_URL'):
    # Railway → PostgreSQL + PostGIS
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,
            engine='django.contrib.gis.db.backends.postgis',
        )
    }
else:
    # Local → ta config PostgreSQL locale
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': 'AirBNB',
            'USER': 'MReus',
            'PASSWORD': 'ikzera13',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

# =====================
# Auth
# =====================
AUTH_USER_MODEL = 'backEnd.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"

# =====================
# Internationalisation
# =====================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# =====================
# Static / Media
# =====================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================
# DRF
# =====================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}

# =====================
# CORS & CSRF
# =====================
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173'
).split(',')

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:5173'
).split(',')