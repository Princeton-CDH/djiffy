# minimal django settings required to run tests

# run against mysql to catch validation issues sqlite doesn't have
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'test',
        'USER': 'root',
        'HOST': 'localhost',
        'PORT': '',
        'TEST': {
                'CHARSET': 'utf8',
                'COLLATION': 'utf8_general_ci',
            },
    }
}

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'dal',
    'dal_select2',
    'djiffy',
)

ROOT_URLCONF = 'djiffy.test_urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
    }
]

# SECRET_KEY = ''
