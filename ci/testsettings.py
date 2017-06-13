# minimal django settings required to run tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test.db",
    }
}

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'djiffy',
)

ROOT_URLCONF = 'djiffy.test_urls'

# SECRET_KEY = ''
