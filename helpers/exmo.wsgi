#!/usr/bin/env python

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exmo.settings")

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
