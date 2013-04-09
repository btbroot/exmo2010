# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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
# Django settings for exmo project.

import os


PROJECT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..')
path_to_project = lambda *a: os.path.join(PROJECT_DIR, *a)


DEBUG = False
TEMPLATE_DEBUG = DEBUG
TEMPLATE_STRING_IF_INVALID = ''

ADMINS = (
    ('Your Name', ''),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'OPTIONS': {
            'init_command': 'SET storage_engine=INNODB',
        },
    }
}


TIME_ZONE = 'Europe/Moscow'

LANGUAGE_CODE = 'ru-RU'

SITE_ID = 1

USE_I18N = True

SITE_PREFIX = '/'

USE_ETAGS = True

MEDIA_URL = '/media/'
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

# path to project media and static files:
MEDIA_ROOT = path_to_project('../media')
STATIC_ROOT = path_to_project('../static')

# path to application static files:
STATICFILES_DIRS = (
    path_to_project('static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = 'zou(k9*+vc69ji$xlpy+e-poi1s6_*q3#0+)=(pgv(wxb&94dd'

MIDDLEWARE_CLASSES = ()

if not DEBUG:
    MIDDLEWARE_CLASSES += (
        'django.middleware.cache.UpdateCacheMiddleware',
    )

MIDDLEWARE_CLASSES += (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django403.middleware.Django403Middleware',
    'breadcrumbs.middleware.BreadcrumbsMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'reversion.middleware.RevisionMiddleware',
)

if not DEBUG:
    MIDDLEWARE_CLASSES += (
        'django.middleware.cache.FetchFromCacheMiddleware',
    )

ROOT_URLCONF = 'exmo.urls'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader'
)

TEMPLATE_DIRS = (
    os.path.join(os.path.abspath(os.path.dirname(__file__)), '../templates'),
)


TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request'
)

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
    # External apps:
    'admin_tools',
    'admin_tools.theming',
    'admin_tools.menu',
    'admin_tools.dashboard',
    'pytils',
    'reversion',
    'south',
    'django403',
    'tagging',
    'tagging_autocomplete',
    'registration',
    'django_wysiwyg',
    'ckeditor',
    'breadcrumbs',
    # Local apps:
    'accounts',
    'auth',
    'breadcrumbs',
    'core',
    'custom_comments',
    'dashboard',
    'digest_email',
    'exmo2010',
    'monitorings',
    'organizations',
    'parameters',
    'scores',
    'tasks',
    'questionnaire',
)

COMMENTS_APP = 'custom_comments'

CSRF_FAILURE_VIEW = 'exmo2010.custom_registration.views.csrf_failure'

DJANGO_WYSIWYG_FLAVOR = "ckeditor"
CKEDITOR_UPLOAD_PATH = MEDIA_ROOT

try:
    import django_extensions
    INSTALLED_APPS = INSTALLED_APPS + ('django_extensions',)
except ImportError:
    pass

if DEBUG:
    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + ('debug_toolbar.middleware.DebugToolbarMiddleware',)
    INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar', 'debug_toolbar_user_panel',)
    INTERNAL_IPS = ('127.0.0.1',)
else:
    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + ('django.middleware.gzip.GZipMiddleware',)


LOCALE_PATHS = (path_to_project('locale'),)

# email server
USE_EMAIL = True
SERVER_EMAIL = 'www-data@svobodainfo.org'
DEFAULT_FROM_EMAIL = SERVER_EMAIL
EMAIL_SUBJECT_PREFIX = '[exmo] '
FORCE_SCRIPT_NAME = ""

# registration
REGISTRATION_OPEN = True
ACCOUNT_ACTIVATION_DAYS = 30
LOGIN_URL = '/exmo2010/accounts/login/'
LOGOUT_URL = '/exmo2010/accounts/logout/'
LOGIN_REDIRECT_URL = '/exmo2010/'
AUTH_PROFILE_MODULE = 'exmo2010.UserProfile'
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'auth.backends.ObjectPermBackend',
)

#tag length
MAX_TAG_LENGTH = 255
#tag autocomlete
TAGGING_AUTOCOMPLETE_JS_BASE_URL = STATIC_URL + "exmo2010"

# cache
CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True
CACHE_PATH = path_to_project('../cache')
CACHE_TIMEOUT = '3600'
#old variant
CACHE_BACKEND = 'file://' + CACHE_PATH + '?timeout=' + CACHE_TIMEOUT
#new variant
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': CACHE_PATH,
        'TIMEOUT': CACHE_TIMEOUT,
    }
}

DATETIME_FORMAT = "Y-m-d, H:i"

ADMIN_TOOLS_INDEX_DASHBOARD = {
    'core.site': 'dashboard.dashboard.CustomIndexDashboard',
    'django.contrib.admin.site': 'admin_tools.dashboard.dashboards.DefaultIndexDashboard',
}

ADMIN_TOOLS_MENU = {
    'core.site': 'dashboard.menu.CustomMenu',
    'django.contrib.admin.site': 'admin_tools.menu.DefaultMenu',
}

ADMIN_TOOLS_THEMING_CSS = 'dashboard/css/theming.css'

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
    'debug_toolbar_user_panel.panels.UserPanel',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

EXMO_PAGINATEBY = 20

DATE_INPUT_FORMATS = (
    '%d.%m.%Y',
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d %Y',
    '%b %d, %Y', '%d %b %Y', '%d %b, %Y', '%B %d %Y',
    '%B %d, %Y', '%d %B %Y', '%d %B, %Y'
)


try:
    from local_settings import *
except ImportError:
    pass
