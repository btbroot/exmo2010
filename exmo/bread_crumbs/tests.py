# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
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
#    along with this program.  If not, see <http://www.gnu.usr/licenses/>.
#
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.translation import ugettext_lazy as _
from model_mommy import mommy
from nose_parameterized import parameterized

from core.utils import get_named_patterns
from exmo2010.models import Monitoring, Organization, Task, MONITORING_PUBLISHED


class ExmoBreadcrumbsTestCase(TestCase):
    ''' Should set proper breadcrumbs for expets and non-experts '''

    # Expected breadcrumbs
    index = [('index', '')]
    ratings = index + [('ratings', _('Ratings'))]
    rating = ratings + [('monitoring_rating', _('Rating'))]

    nonexpert_task_scores = rating + [('score_list_by_task', _('Organization'))]

    expert_task_scores = index + [
        ('monitorings_list', _('Monitoring cycles')),
        ('tasks_by_monitoring', _('Monitoring cycle')),
        ('score_list_by_task', _('Organization'))
    ]

    def setUp(self):
        # GIVEN published monitoring, organization and approved task
        monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        organization = mommy.make(Organization, monitoring=monitoring)
        task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)

        # AND expertA account
        expertA = User.objects.create_user('expertA', 'u@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True

        # AND kwargs to reverse view urls
        self.kwargs = {
            'monitoring_pk': monitoring.pk,
            'task_pk': task.pk,
            'org_pk': organization.pk
        }

        # AND dict of all urlpatterns by urlname
        self.patterns_by_name = dict((p.name, p) for p in get_named_patterns())

    def _reverse(self, urlname):
        ''' reverse urlname with needed kwargs '''
        pat = self.patterns_by_name[urlname]
        kwargs = dict((k, self.kwargs[k]) for k in pat.regex.groupindex if k in self.kwargs)
        return reverse(pat._full_name, kwargs=kwargs)

    def _reversed_crumbs(self, expected):
        for urlname, title in expected:
            yield {'urlname': urlname, 'url': self._reverse(urlname), 'title': title}

    @parameterized.expand([
        ('index', index),
        ('ratings', ratings),
        ('monitoring_rating', rating),
        ('score_list_by_task', nonexpert_task_scores),
        ('score_list_by_task', expert_task_scores, True),
    ])
    def test_crumbs(self, urlname, expected_crumbs, is_expert=False):
        if is_expert:
            # WHEN i login as expertA
            self.client.login(username='expertA', password='password')

        # WHEN i get the page
        res = self.client.get(self._reverse(urlname))
        # THEN status code is 200
        self.assertEqual(res.status_code, 200)

        # AND crumbs are equal to expected
        expected_crumbs = list(self._reversed_crumbs(expected_crumbs))
        self.assertEqual(res.context['breadcrumbs'], expected_crumbs)
