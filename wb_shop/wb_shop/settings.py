import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

from core.constants import LoggingConstants, SettingsConstants, TokenConstants

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
DEBUG = os.getenv('DEBUG', 'false').lower() in ('true', '1', 't')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')

LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOGGING = {
    'version': LoggingConstants.CONFIG_VERSION,
    'disable_existing_loggers': False,

    'formatters': {
        'log_style': {
            'format': '{asctime} | {levelname} | {name} | {message}',
            'style': '{',
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'log_style',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'maxBytes': LoggingConstants.FILE_MAX_SIZE,
            'backupCount': LoggingConstants.BACKUP_COUNT,
            'formatter': 'log_style',
            'encoding': 'utf-8',
        },
    },

    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}


INSTALLED_APPS = [
    'api.apps.ApiConfig',
    'product.apps.ProductConfig',
    'user.apps.UserConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'drf_spectacular',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wb_shop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wb_shop.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB'),
        'USER': os.getenv('POSTGRES_USER'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD'),
        'HOST': os.getenv('POSTGRES_HOST'),
        'PORT': os.getenv('POSTGRES_PORT'),
    }
}


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


LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'user.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': (
        'rest_framework.pagination.PageNumberPagination'
    ),
    'PAGE_SIZE': SettingsConstants.PAGINATION_PAGE_NUMBER,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = 'noreply@wbshop.com'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=TokenConstants.EXPIRE_ACCESS_MINUTS,
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=TokenConstants.EXPIRE_REFRESH_DAYS,
    ),

    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,

    'AUTH_HEADER_TYPES': ('Bearer',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'WB Shop',
    'DESCRIPTION': (
        'Интернет-магазин WB Shop. '
        'Позволяет пользователям просматривать товары, управлять корзиной '
        'и оформлять заказы. Администратору доступны управление товарами, '
        'пользователями и заказами.\n\n'

        'Проект представляет собой MVP бэкенда с REST API.\n\n'

        'Полезные материалы:\n'
        '- [GitHub репозиторий]('
        'https://github.com/TimurBikmaev/wb_shop)\n'

        '- [README.md]('
        'https://github.com/TimurBikmaev/wb_shop/'
        'blob/main/README.md)\n\n'

        '- [Источник документации Swagger]('
        'https://github.com/TimurBikmaev/wb_shop/'
        'blob/main/wb_shop/docs/wb_shop.yaml)\n\n'

        'Связь с разработчиком:\n'
        '- [Telegram](https://t.me/w_NeVeR_w)\n'
        '- Почта: bikma2004@gmail.com\n'
        '- [Портфолио](https://github.com/TimurBikmaev)\n'
    ),
    'TAGS': [
        {
            'name': 'Аутентификация',
            'description': 'Регистрация и подтверждение пользователя',
        },
        {
            'name': 'Пользователи',
            'description': 'Профиль пользователя и управление балансом',
        },
        {
            'name': 'Товары',
            'description': 'Просмотр и управление товарами магазина',
        },
        {
            'name': 'Корзина',
            'description': 'Просмотр и управление содержимым корзины',
        },
        {
            'name': 'Заказы',
            'description': 'Просмотр и управление заказами',
        },
    ],
    'COMPONENT_SPLIT_REQUEST': True,
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
