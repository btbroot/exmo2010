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
from django.core.management import call_command
from django.test import TransactionTestCase
from model_mommy import mommy

from south.migration import Migrations


class MigrationTestCase(TransactionTestCase):
    """
    Base TestCase for testing migrations. Subclasses should define app to work with.
    """

    app = None

    def setUp(self):
        super(MigrationTestCase, self).setUp()

        # Ensure the migration history is up-to-date with a fake migration.
        # The other option would be to use the south setting for these tests
        # so that the migrations are used to setup the test db.
        call_command('migrate', self.app, fake=True, verbosity=0)

    def tearDown(self):
        # Leave the db in the final state so that the test runner doesn't
        # error when truncating the database.
        call_command('migrate', self.app, verbosity=0)

    def migrate(self, target):
        """ Migrate and return target orm handler. """
        call_command('migrate', self.app, target, verbosity=0)
        return Migrations(self.app).guess_migration(target).orm()


class Exmo2010MigrationsTestCase(MigrationTestCase):
    app = 'exmo2010'

    def test_0023_urls_to_links_data_migration(self):
        # Migrate back to migration 0022.
        orm = self.migrate('0022')

        # GIVEN task and 2 scores
        task = mommy.make(orm.Task)
        mommy.make(orm.Score, task=task, foundComment='lol', accessibleComment='ya')
        mommy.make(orm.Score, task=task, foundComment=None, accessibleComment='ya', completeComment='123')

        # Apply datamigration
        orm = self.migrate('0023_urls_to_links_data_migration')

        # All "*Comment" score fields should be concatenated with newlines and stored in "foundComment" field
        scores = orm.Score.objects.values_list('foundComment', 'accessibleComment', 'completeComment')
        self.assertEqual(set(scores), set([('lol\nya', 'ya', None), ('\n123\nya', 'ya', '123')]))

    def test_0039_fix_email_confirmed_status_data_migration(self):
        # Migrate back to migration 0038.
        orm = self.migrate('0038')

        Group = orm['auth.Group']
        UserProfile = orm['exmo2010.UserProfile']

        # GIVEN confirmed email active user
        mommy.make(UserProfile, user__is_active=True, user__username='active_user')
        # AND confirmed email inactive user
        mommy.make(UserProfile, user__is_active=False, user__username='inactive_user')
        # AND confirmed email active expert
        mommy.make(UserProfile, user__is_active=True, user__username='active_expert',
                   user__groups=[Group.objects.get(name='expertsA')])
        # AND confirmed email inactive expert
        mommy.make(UserProfile, user__is_active=False, user__username='inactive_expert',
                   user__groups=[Group.objects.get(name='expertsB')])

        # Apply datamigration
        orm = self.migrate('0039_fix_email_confirmed_status_data_migration')

        UserProfile = orm['exmo2010.UserProfile']

        # Users who confirmed email should be active user and both experts
        email_confirmed_users = UserProfile.objects.filter(email_confirmed=True)
        self.assertEqual(set(email_confirmed_users.values_list('user__username', flat=True)),
                         {'active_user', 'active_expert', 'inactive_expert'})
        # User who not confirmed email should be inactive user
        email_not_confirmed_users = UserProfile.objects.filter(email_confirmed=False)
        self.assertEqual(set(email_not_confirmed_users.values_list('user__username', flat=True)),
                         {'inactive_user'})
