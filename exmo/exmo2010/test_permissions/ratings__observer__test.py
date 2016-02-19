# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2016 IRSI LTD
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
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy

from exmo2010.models import Monitoring, Organization, ObserversGroup, PUB, INT


class ObserversGroupRatingsTableVisibilityTestCase(TestCase):
    # exmo2010:ratings

    # On ratings page observers should see only
    # published monitorings and those with observed organizations

    def setUp(self):
        # GIVEN published monitoring
        self.mon_published = mommy.make(Monitoring, status=PUB)
        # AND published hidden monitoring
        self.mon_published_hidden = mommy.make(Monitoring, status=PUB, hidden=True)
        # AND interaction monitoring
        self.mon_interaction = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring
        self.mon_interaction_hidden = mommy.make(Monitoring, status=INT, hidden=True)
        # AND interaction monitoring with observed organizations
        self.mon_interaction_with_observed_orgs = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring with observed organizations
        self.mon_interaction_hidden_with_observed_orgs = mommy.make(Monitoring, status=INT, hidden=True)

        # AND 1 organization in interaction monitoring with observed organizations
        organization_1 = mommy.make(Organization, monitoring=self.mon_interaction_with_observed_orgs)
        # AND 1 organization in interaction hidden monitoring with observed organizations
        organization_2 = mommy.make(Organization, monitoring=self.mon_interaction_hidden_with_observed_orgs)

        # AND observer account
        observer = User.objects.create_user('observer', 'observer@svobodainfo.org', 'password')
        # AND observers group for interaction monitoring with observed organizations
        obs_group_1 = mommy.make(ObserversGroup, monitoring=self.mon_interaction_with_observed_orgs)
        obs_group_1.organizations = [organization_1]
        obs_group_1.users = [observer]
        # AND observers group for interaction hidden monitoring with observed organizations
        obs_group_2 = mommy.make(ObserversGroup, monitoring=self.mon_interaction_hidden_with_observed_orgs)
        obs_group_2.organizations = [organization_2]
        obs_group_2.users = [observer]

        # AND I logged in as observer
        self.client.login(username='observer', password='password')

    def test_visible_monitorings(self):
        # WHEN I get ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND context should contain expected monitorings count
        expected_pks = {self.mon_published.pk,
                        self.mon_interaction_with_observed_orgs.pk,
                        self.mon_interaction_hidden_with_observed_orgs.pk}
        self.assertEqual(set(m.pk for m in response.context['monitoring_list']), expected_pks)
