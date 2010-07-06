# Copyright 2010 Al Nikolov <root@root.spb.ru>, Helsinki, Finland
# Copyright 2010 Institute of Information Freedom Development, non-profit partnership, Saint-Petersburg, Russia
#
# This file is part of EXMO2010 software.
#
# EXMO2010 is NOT distributable. NOBODY is permitted to use it without a written permission from the
# above copyright holders.
#!/usr/bin/python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)
