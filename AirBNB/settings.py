from pathlib import Path
import os
import dj_database_url

# === GeoDjango / GDAL Setup ===
import os
import ctypes

# Chemin vers la DLL GDAL dans ton venv
GDAL_DLL_PATH = r"D:\AirBNB\.venv\Lib\site-packages\osgeo\gdal304.dll"

# Forcer le chargement de la DLL avant tout import Django
ctypes.CDLL(GDAL_DLL_PATH)

# Indiquer à Django où trouver GDAL
GDAL_LIBRARY_PATH = GDAL_DLL_PATH

BASE_DIR = Path(__file__).resolve().parent.parent

# Secrets et debug
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-default-key")
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Applications
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

    # 3rd party
    'django_cleanup.apps.CleanupConfig',
    'rest_framework',
    'rest_framework_gis',

    # Local
    'backEnd',
    'frontEnd',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
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

# Base de données
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


# Auth
AUTH_USER_MODEL = 'backEnd.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalisation
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static / Media
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
#STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",   # public par défaut
    ],
}

CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "https://*.onrender.com"
).split(",")

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

SESSION_ENGINE = "django.contrib.sessions.backends.db"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]
