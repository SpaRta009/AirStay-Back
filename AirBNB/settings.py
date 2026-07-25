from pathlib import Path
import os
import sys
import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================
# ✅ Config GDAL/GEOS pour Windows (dev local)
# =====================
if sys.platform == "win32":
    GDAL_DIR = r"C:\Program Files\GDAL"

    GDAL_DLL_PATH = os.path.join(GDAL_DIR, "gdal311.dll")
    if os.path.exists(GDAL_DLL_PATH):
        GDAL_LIBRARY_PATH = GDAL_DLL_PATH

    # Recherche automatique de geos_c.dll (fourni par shapely dans le venv)
    try:
        import shapely
        GEOS_CANDIDATES = list(Path(shapely.__file__).parent.rglob("geos_c*.dll"))
        if GEOS_CANDIDATES:
            GEOS_LIBRARY_PATH = str(GEOS_CANDIDATES[0])
    except ImportError:
        pass

    # Données GDAL (proj, epsg, etc.) — laissé en best-effort, ne bloque pas si absent
    _gdal_data = os.path.join(GDAL_DIR, "gdal-data")
    _proj_lib = os.path.join(GDAL_DIR, "projlib")
    if os.path.exists(_gdal_data):
        os.environ['GDAL_DATA'] = _gdal_data
    if os.path.exists(_proj_lib):
        os.environ['PROJ_LIB'] = _proj_lib

    os.environ['PATH'] = GDAL_DIR + os.pathsep + os.environ.get('PATH', '')

# =====================
# Sécurité
# =====================
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1'
).split(',')

# ✅ Railway est derrière un proxy HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

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
    #'django_cleanup.apps.CleanupConfig',
    'rest_framework',
    'rest_framework_gis',
    # ✅ Cloudinary
    'cloudinary',
    'cloudinary_storage',
    'backEnd',
]

# =====================
# Middleware
# =====================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}
DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'
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
# Static files
# =====================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =====================
# ✅ Media via Cloudinary (persist entre les déploiements)
# =====================
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY':    os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
    # CRITICAL FIXES FOR 404 ERRORS:
    'SECURE': True,      # Forces HTTPS connections
    'SIGN_URL': False,   # Prevents Cloudinary from appending the 24-hour expiration token
}

# Si Cloudinary est configuré → utiliser Cloudinary pour les médias
# Sinon → fallback local (dev)
if os.environ.get('CLOUDINARY_CLOUD_NAME'):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    MEDIA_URL = '/media/'
else:
    # Local dev
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
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://project-tqvp7.vercel.app",
]

CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "https://project-tqvp7.vercel.app",
]