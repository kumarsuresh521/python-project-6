import os
import datetime
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ["*"]
# Application definition


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'drf_multiple_model',
    'django_prometheus',
    'django_stomp',
    'corsheaders'
]

LOCAL_APPS = [
    'app',
]

INSTALLED_APPS += THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',  # Mandatory
    'django.middleware.security.SecurityMiddleware',  # Mandatory
    'django.contrib.sessions.middleware.SessionMiddleware',  # Mandatory
    'django.middleware.common.CommonMiddleware',  # Mandatory
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Mandatory
    'django.contrib.messages.middleware.MessageMiddleware',  # Mandatory
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Mandatory
    'django_prometheus.middleware.PrometheusAfterMiddleware', # Mandatory
    'corsheaders.middleware.CorsMiddleware',
]

# https://stackoverflow.com/questions/28071862/django-sessionid-cookie-is-this-a-security-failure
# https://security.stackexchange.com/questions/8964/trying-to-make-a-django-based-site-use-https-only-not-sure-if-its-secure/8970#8970


SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True

SESSION_EXPIRE_AT_BROWSER_CLOSE=True

SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

X_FRAME_OPTIONS = "DENY" # DENY
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = False

ROOT_URLCONF = 'route.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'app','static')],
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

WSGI_APPLICATION = 'route.wsgi.application'
PG_HOST = "localhost"
PG_PORT = 5432
PG_USER = "postgres"
PG_PASS = "root"
PG_DB_NAME = "development"

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'X-KC-Token',
    'X-Proxy-Claims',
    'X-Token-Status'
]


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': PG_DB_NAME,
        'USER': PG_USER,
        'PASSWORD': PG_PASS,
        'HOST': PG_HOST,
        'PORT': PG_PORT,
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    )
}

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/stattic/'

STATIC_ROOT = os.path.join(BASE_DIR, 'app/static')

'''
New Settings
'''

ELASTIC_SEARCH_INDEX_KEY = "contracts_data"

ELASTIC_EXTRACTED_INDEX_KEY = "extracted_documents"

APTTUS_DOCUMENTS_INDEX_KEY = "apt_documents"

DOCUMENT_TREE_INDEX_KEY = "document_tree"

MAX_UPLOAD_SIZE = 104857600

DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600

IS_NOTIFICATION_REQUIRED = True

STOMP_SERVER_HOST = 'activemq'
STOMP_SERVER_PORT = 8080
STOMP_USE_SSL = False
STOMP_SERVER_USER = "xxxxxxxxx"
STOMP_SERVER_PASSWORD = "xxxxxxxxxx"
STOMP_CORRELATION_ID_REQUIRED = False
STOMP_TOPIC_NAME = "xxxxxxxxx"

if 'staging' in str(os.environ.get("NAMESPACE")):
    ENV_PLAT='staging'
    S3_BUCKET=str(os.environ.get("NAMESPACE")).split('-staging')[0]
else:
    ENV_PLAT='production'
    S3_BUCKET=str(os.environ.get("NAMESPACE")).split('-production')[0]


S3_BUCKET_TESTING_SG_PATH = ENV_PLAT+"/contracts_dataset/testing_sg/{}"
S3_BUCKET_TXT_VERSION_PATH = ENV_PLAT+"/contracts_detected_objects/txt_version/raw/{}.txt"
S3_BUCKET_CSV_VERSION_PATH =ENV_PLAT+"/contracts_detected_objects/csv_version/{}_text.csv"
S3_BUCKET_EXTRACTED_IMAGES_PATH = ENV_PLAT+"/contracts_detected_objects/extracted_images/{}/"
S3_BUCKET_SEARCHABLE_PDF_PATH = ENV_PLAT+"/contracts_detected_objects/searchable_pdfs/{}"
S3_BUCKET_OUTPUT_PATH = ENV_PLAT+"/output/{}.json"
S3_BUCKET_APTTUS_PDF_PATH = ENV_PLAT+"/contracts_dataset/apttus/{}"
S3_BUCKET_SEARCHABLE_APTTUS_PDF_PATH = ENV_PLAT+"/contracts_detected_objects/searchable_pdfs/apttus/{}"
S3_BUCKET_CUSTOMER_FILES_PATH = ENV_PLAT+"/customer_files"

S3_BUCKET_PATH =ENV_PLAT+"/contracts_dataset"
S3_BUCKET_LOCAL_PATH = "se"
S3_BUCKET_DE_FILES_PATH = ENV_PLAT+"/de_files"

S3_ENDPOINT_URL = "https://xxxxxxxxxxxxxxxxxxxxxxxxxx"
S3_ACCESS_KEY = "xxxxxxxxxxxxxxxxxxxxx"
S3_SECRET_KEY = "xxxxxxxxxxxxxxxxxxxxx"
S3DIRECT_REGION = "es-asia"
