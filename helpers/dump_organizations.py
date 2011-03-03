#!/usr/bin/python

'''
dump organizations as text file
'''


import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = "exmo.settings"
path = "%s/.." % os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.realpath(path))

from exmo.exmo2010.models import Organization

f = open('sud.txt', 'w')
for org in Organization.objects.filter(type__pk = '3'):
    s='%s %s\n' % ( org.pk, org.name )
    s=s.encode('utf-8')
    f.write(s)

f.close()
