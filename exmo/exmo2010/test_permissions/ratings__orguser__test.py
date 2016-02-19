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
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy

from exmo2010.models import Monitoring, Organization, OrgUser, PUB, INT


class OrgUserRatingsTableVisibilityTestCase(TestCase):
    # exmo2010:ratings

    # On ratings page organization representative should see only
    # published monitorings and those with related organizations

    def setUp(self):
        # GIVEN published monitoring
        self.mon_published = mommy.make(Monitoring, status=PUB)
        # AND published hidden monitoring
        self.mon_published_hidden = mommy.make(Monitoring, status=PUB, hidden=True)
        # AND interaction monitoring
        self.mon_interaction = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring
        self.mon_interaction_hidden = mommy.make(Monitoring, status=INT, hidden=True)
        # AND interaction monitoring with representative
        self.mon_interaction_with_representative = mommy.make(Monitoring, status=INT)
        # AND interaction hidden monitoring with representative
        self.mon_interaction_hidden_with_representative = mommy.make(Monitoring, status=INT,
                                                                     hidden=True)
        # AND 1 organization in interaction monitoring with representative
        organization_1 = mommy.make(Organization, monitoring=self.mon_interaction_with_representative)
        # AND 1 organization in interaction hidden monitoring with representative
        organization_2 = mommy.make(Organization, monitoring=self.mon_interaction_hidden_with_representative)

        # AND organization representative account
        org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        org.groups.add(Group.objects.get(name=org.profile.organization_group))
        mommy.make(OrgUser, organization=organization_1, userprofile=org.profile)
        mommy.make(OrgUser, organization=organization_2, userprofile=org.profile)

        # AND I logged in as organization representative
        self.client.login(username='org', password='password')

    def test_visible_monitorings(self):
        # WHEN I get ratings page
        response = self.client.get(reverse('exmo2010:ratings'))
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND context should contain expected monitorings count
        expected_pks = {self.mon_published.pk,
                        self.mon_interaction_with_representative.pk,
                        self.mon_interaction_hidden_with_representative.pk}
        self.assertEqual(set(m.pk for m in response.context['monitoring_list']), expected_pks)
