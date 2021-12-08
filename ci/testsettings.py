# minimal django settings required to run tests
import os

# run against postgresql
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "USER": os.getenv("DB_USER"),
        "NAME": os.getenv("DB_NAME"),
        "HOST": "127.0.0.1",
    }
}

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "dal",
    "dal_select2",
    "djiffy",
)

ROOT_URLCONF = "djiffy.test_urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
    }
]

# SECRET_KEY = ''
