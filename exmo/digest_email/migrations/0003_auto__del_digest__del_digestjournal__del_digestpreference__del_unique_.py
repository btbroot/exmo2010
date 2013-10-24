# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Foundation "Institute for Information Freedom Development"
# Copyright 2013 Al Nikolov
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
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'DigestPreference', fields ['user', 'digest']
        db.delete_unique('digest_email_digestpreference', ['user_id', 'digest_id'])

        # Deleting model 'Digest'
        db.delete_table('digest_email_digest')

        # Deleting model 'DigestJournal'
        db.delete_table('digest_email_digestjournal')

        # Deleting model 'DigestPreference'
        db.delete_table('digest_email_digestpreference')


    def backwards(self, orm):
        # Adding model 'Digest'
        db.create_table('digest_email_digest', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, unique=True)),
        ))
        db.send_create_signal('digest_email', ['Digest'])

        # Adding model 'DigestJournal'
        db.create_table('digest_email_digestjournal', (
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('digest', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['digest_email.Digest'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('digest_email', ['DigestJournal'])

        # Adding model 'DigestPreference'
        db.create_table('digest_email_digestpreference', (
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('digest', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['digest_email.Digest'])),
            ('interval', self.gf('django.db.models.fields.PositiveIntegerField')(default=5)),
        ))
        db.send_create_signal('digest_email', ['DigestPreference'])

        # Adding unique constraint on 'DigestPreference', fields ['user', 'digest']
        db.create_unique('digest_email_digestpreference', ['user_id', 'digest_id'])


    models = {

    }

    complete_apps = ['digest_email']