# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os
import sys

from django.core.urlresolvers import reverse_lazy


DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Your Name', ''),
)
MANAGERS = ADMINS

PROJECT_NAME = 'exmo'

# Celery
CELERY_IMPORTS = ('exmo2010.celery_tasks',)
BROKER_URL = 'mongodb://user:password@hostname:port/database_name'
CELERY_RESULT_BACKEND = 'database'
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_ACCEPT_CONTENT = ['pickle']
CELERY_ALWAYS_EAGER = False
CELERY_TASK_RESULT_EXPIRES = 18000
CELERY_SEND_TASK_ERROR_EMAILS = True
# settings for sending email task
EMAIL_DEFAULT_RETRY_DELAY = 10 * 60  # seconds
EMAIL_MAX_RETRIES = 5
EMAIL_RATE_LIMIT = '100/m'

# Databases
MYSQL_INIT = [
    'SET storage_engine = INNODB',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'OPTIONS': {
            'init_command': '; '.join(MYSQL_INIT),
        },
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_unicode_ci',
    }
}

# Tests
TEST = 'test' in sys.argv
if TEST:
    SOUTH_TESTS_MIGRATE = False
    # execute celery tasks immediately
    CELERY_ALWAYS_EAGER = True
    # in-memory SQLite used for testing.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# A secret key for this particular Django installation. Used in secret-key hashing algorithms.
SECRET_KEY = ''

# Localization
TIME_ZONE = 'Europe/Moscow'
LANGUAGE_CODE = 'en'
LANGUAGES = (
    ('ru', 'Русский'),
    ('en', 'English'),
    ('ka', 'ქართული'),
    ('az', 'Azərbaycanca'),
)
USE_L10N = True
SITE_ID = 1
USE_I18N = True

# MODELTRANSLATION_FALLBACK_LANGUAGES will be used as fallback language if some model does not
# have transalted field to other language.
MODELTRANSLATION_FALLBACK_LANGUAGES = ('en', 'ru', 'ka', 'az')

USE_ETAGS = True
FORMAT_MODULE_PATH = 'formats'
LOCALE_PATHS = ('locale',)

MEDIA_URL = '/media/'
STATIC_URL = '/static/'

MEDIA_ROOT = '/var/lib/exmo2010'
STATIC_ROOT = '/usr/share/exmo2010'

STATICFILES_DIRS = ('static',)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Cache
CACHE_PATH = '/var/cache/exmo2010/'
CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True
CACHE_PREFIX = 'Cache'
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': CACHE_PATH,
        'KEY_PREFIX': '',
        'TIMEOUT': 300,
    }
}

# CKEditor config
CKEDITOR_UPLOAD_PATH = 'ckeditor_uploads/'
CKEDITOR_IMAGE_BACKEND = 'pillow'
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'All',
    },
    'simplified': {
        'toolbar': [['Bold', 'Italic', 'Underline', '-', 'NumberedList', 'BulletedList', '-', 'Link', 'Unlink']],
        'height': 200,
        'width': '100%',
        # hide bottom toolbar:
        'removePlugins': 'elementspath',
        'resize_enabled': False,
    },
    'advanced': {
        'toolbar': [
            {'name': 'document', 'items': ['Source', '-', 'Preview', 'Templates']},
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'paragraph', 'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote',
                                            'CreateDiv', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight',
                                            'JustifyBlock']},
            {'name': 'insert', 'items': ['Image', 'Table', 'HorizontalRule', 'SpecialChar', '-', 'Maximize']},
            '/',
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-',
                                              'RemoveFormat']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'editing', 'items': ['Find', 'Replace']},
            {'name': 'styles', 'items': ['Styles', 'Format', 'Font', 'FontSize']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
        ],
        # disable collapse button:
        'toolbarCanCollapse': False,
        # hide bottom toolbar:
        'removePlugins': 'elementspath',
        'resize_enabled': False,
    },
}

# Middleware
MIDDLEWARE_CLASSES = ()

if not DEBUG:
    MIDDLEWARE_CLASSES += (
        'django.middleware.cache.UpdateCacheMiddleware',
    )

MIDDLEWARE_CLASSES += (
    'exmo2010.middleware.StaticDataInitMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'exmo2010.middleware.CustomLocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django403.middleware.Django403Middleware',
    'django.middleware.transaction.TransactionMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'bread_crumbs.middleware_exmo.ExmoBreadcrumbsMiddleware',
)

if not DEBUG:
    MIDDLEWARE_CLASSES += (
        'django.middleware.cache.FetchFromCacheMiddleware',
    )

# URLs
ROOT_URLCONF = 'exmo.urls'

# Templates
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
TEMPLATE_DIRS = ('templates',)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    'core.context_processors.user_groups',
    'exmo2010.context_processors.exmo_models',
    'exmo2010.context_processors.live_settings',
    'exmo2010.context_processors.text_fragments',
)

# Applications
INSTALLED_APPS = (
    # Built-in django apps:
    'django.contrib.auth',
    'django.contrib.comments',
    'django.contrib.staticfiles',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.formtools',
    # External apps:
    'admin_tools',
    'admin_tools.theming',
    'admin_tools.menu',
    'admin_tools.dashboard',
    'livesettings',
    'keyedcache',
    'reversion',
    'south',
    'djcelery',
    'django403',
    'registration',
    'ckeditor',
    'modeltranslation',
    'widget_tweaks',
    # Local apps:
    'accounts',
    'auth',
    'claims',
    'clarifications',
    'core',
    'custom_comments',
    'dashboard',
    'exmo2010',
    'monitorings',
    'organizations',
    'parameters',
    'scores',
    'tasks',
    'questionnaire',
)

if TEST:
    INSTALLED_APPS += ('django_nose',)

# Admin tools
ADMIN_TOOLS_INDEX_DASHBOARD = 'dashboard.dashboard.CustomIndexDashboard'
ADMIN_TOOLS_MENU = 'dashboard.menu.CustomMenu'
ADMIN_TOOLS_THEMING_CSS = 'dashboard/css/theming.css'

# Customization
COMMENTS_APP = 'custom_comments'
CSRF_FAILURE_VIEW = 'exmo2010.custom_registration.views.csrf_failure'

# E-mail
SERVER_EMAIL = 'www-data@svobodainfo.org'
IMAP_SERVER = 'imap.example.com'
IMAP_LOGIN = 'example@example.com'
IMAP_PASSWORD = 'password'

# Registration
CUSTOM_REGISTRATION_BACKEND = 'exmo2010.custom_registration.backends.CustomBackend'
ACCOUNT_ACTIVATION_DAYS = 30
LOGIN_URL = reverse_lazy('exmo2010:auth_login')
LOGOUT_URL = reverse_lazy('exmo2010:auth_logout')
LOGIN_REDIRECT_URL = reverse_lazy('exmo2010:index')
AUTH_PROFILE_MODULE = 'exmo2010.UserProfile'
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'auth.backends.ObjectPermBackend',
)

# Tags
MAX_TAG_LENGTH = 255
TAGGING_AUTOCOMPLETE_JS_BASE_URL = STATIC_URL + "exmo2010"

DEVEL = False

if os.path.isfile('%s/local_settings.py' % PROJECT_NAME):
    from local_settings import *


def mkdir_ifnotexist(path):
    os.path.exists(path) or os.makedirs(path)
    return path

if DEVEL or TEST:
    PROJECT_DIR = os.path.abspath(PROJECT_NAME)
    path_to_project = lambda *a: os.path.join(PROJECT_DIR, *a)
    CACHE_PATH = mkdir_ifnotexist(path_to_project('../../cache'))
    MEDIA_ROOT = mkdir_ifnotexist(path_to_project('../../media'))
    STATIC_ROOT = mkdir_ifnotexist(path_to_project('../../static'))

