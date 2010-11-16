#!/usr/bin/python

import sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from django.core.servers.fastcgi import runfastcgi

runfastcgi(
    method="threaded",
    daemonize="false",
    pidfile="/tmp/exmo.pid"
    )
