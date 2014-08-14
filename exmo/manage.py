#!/usr/bin/env python
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
import logging
import os
import sys
import uuid


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exmo.settings")

    from django.core.management import execute_from_command_line

    secret_key_file = 'exmo/django_key'
    if not os.path.exists(secret_key_file):
        logging.info(u'*** Creating random secret key file %s' % secret_key_file)
        with open(secret_key_file, 'w+') as f:
            f.write(str(uuid.uuid4()))

    execute_from_command_line(sys.argv)
