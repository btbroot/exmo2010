# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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
import sys
import getpass

import MySQLdb
from django.contrib.auth import models as auth_app
from django.core.management import call_command
from django.core.management.sql import emit_post_sync_signal
from south.management.commands.syncdb import Command as SouthSyncdb


class Command(SouthSyncdb):
    help = "Create the DB, user for managing this DB and all tables. Run all migrations. Create superuser account."

    def execute(self, *args, **options):
        from django.conf import settings
        alias = options.get('database')
        db_settings = settings.DATABASES.get(alias)

        if not db_settings['USER'] or not db_settings['PASSWORD'] or not db_settings['NAME']:
            sys.stderr.write('Error: fields "USER", "PASSWORD" and "NAME" in settings.DATABASES should not be empty!\n')
            sys.exit(1)

        sys.stdout.write('Installing MySQL database...\n')
        admin = raw_input('MySQL admin name: ')
        password = getpass.getpass('MySQL admin password: ')

        kwargs = dict(user=admin, passwd=password)
        if db_settings['HOST'].startswith('/'):
            kwargs['unix_socket'] = db_settings['HOST']
        elif db_settings['HOST']:
            kwargs['host'] = db_settings['HOST']

        connection = MySQLdb.connect(**kwargs)
        cursor = connection.cursor()

        sql_commands = [
            'CREATE DATABASE IF NOT EXISTS %(NAME)s CHARACTER SET utf8 COLLATE utf8_unicode_ci;',
            'GRANT ALL ON %(NAME)s.* TO %(USER)s@localhost IDENTIFIED BY "%(PASSWORD)s";',
            'SET GLOBAL innodb_file_format = BARRACUDA',
            'SET GLOBAL innodb_file_format_max = BARRACUDA',
            'SET GLOBAL innodb_file_per_table = ON',
            'SET GLOBAL innodb_large_prefix = ON',
        ]

        sys.stdout.write('Creating MySQL database...\n')
        for sql_command in sql_commands:
            sql_query = sql_command % db_settings
            try:
                cursor.execute(sql_query)
            except Exception as e:
                sys.stderr.write('Error: %s\n%s\n' % (sql_query, e))
                sys.exit(1)
            else:
                sys.stdout.write('OK: %s\n' % sql_query)

        super(Command, self).execute(*args, **options)

    def handle_noargs(self, **options):
        # disable superuser creating on this stage
        options['interactive'] = False
        super(Command, self).handle_noargs(**options)
