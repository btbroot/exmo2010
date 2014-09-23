# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from model_mommy import mommy
from nose.plugins.attrib import attr

from core.test_utils import BaseSeleniumTestCase
from exmo2010.models import Task, Organization
from exmo2010.models import Monitoring, MONITORING_PUBLISHED


@attr('selenium')
class OpennessInitialColumnTestCase(BaseSeleniumTestCase):
    # Scenario: Check if initial openness column is display
    modal_window = '.modal-open'
    init_openness = '.init-openness'

    def setUp(self):
        # GIVEN expert B account
        expertB = User.objects.create_user('expertB', 'expertB@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        # AND published monitoring
        self.monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        # AND organzation at this monitoring
        self.organization = mommy.make(Organization, monitoring=self.monitoring)
        # AND task for expert B
        self.task = mommy.make(
            Task,
            organization=self.organization,
            user=expertB,
            status=Task.TASK_APPROVED,
        )

        self.url = reverse('exmo2010:monitoring_rating', args=[self.monitoring.pk])

    def test_anonymous(self):
        # WHEN anonymous get rating page
        self.get(self.url)
        # AND get initial openness column and modal window
        init_openness = self.find(self.init_openness)
        modal = self.find(self.modal_window)
        # THEN initial openness column and modal window should not be existed
        self.assertEqual(init_openness, None)
        self.assertEqual(modal, None)

    def test_users(self):
        # WHEN I am logged in as expert B
        self.login('expertB', 'password')
        # AND get rating page
        self.get(self.url)
        # AND get initial openness column
        init_openness = self.find(self.init_openness)
        # THEN initial openness column should not be existed
        self.assertEqual(init_openness, None)

        # WHEN I click to modal window
        self.find(self.modal_window).click()
        # THEN checkboxes should become visible
        self.assertVisible('#id_rt_initial_openness')
        # WHEN i click initial openness checkbox
        self.find('#id_rt_initial_openness').click()
        # AND submit my changes
        self.find('#modal_window input[type="submit"]').click()
        # THEN initial openness column should be displayed
        self.assertEqual(self.find(self.init_openness).is_displayed(), True)


@attr('selenium')
class DonorsCheckboxDependencyTestCase(BaseSeleniumTestCase):
    # exmo2010:monitoring_copy

    # Donors checkboxes should be enabled/disabled or checked/unchecked depending on current selection.
    # * scores should only be enabled if parameters and tasks are checked.
    # * checking "All" checkbox should disable and check all other checkboxes.
    # * checking "all_scores" checkbox should check "current_scores" checkbox.

    def setUp(self):
        # GIVEN expert A account
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        # AND monitoring
        monitoring = mommy.make(Monitoring)
        # AND monitoring copy page url
        self.url = reverse('exmo2010:monitoring_copy', args=[monitoring.pk])
        # AND I logged in as expert A
        self.login('expertA', 'password')
        # AND get monitoring copy page
        self.get(self.url)

    def test_checkboxes_initial_state(self):
        # WHEN I get this page
        # THEN 'organizations' checkbox should be selected and disabled
        self.assertEqual(self.find('input[value="organizations"]').is_selected(), True)
        self.assertEqual(self.find('input[value="organizations"]').is_enabled(), False)
        # AND 'all_scores' checkbox shouldn't be selected and should be disabled
        self.assertEqual(self.find('input[value="all_scores"]').is_selected(), False)
        self.assertEqual(self.find('input[value="all_scores"]').is_enabled(), False)
        # AND 'current_scores' checkbox shouldn't be selected and should be disabled
        self.assertEqual(self.find('input[value="current_scores"]').is_selected(), False)
        self.assertEqual(self.find('input[value="current_scores"]').is_enabled(), False)

    def test_scores_checkboxes_availability(self):
        # WHEN I get this page and click to 'parameters' and 'tasks' checkboxes
        self.find('input[value="parameters"]').click()
        self.find('input[value="tasks"]').click()
        # THEN 'all_scores' and 'current_scores' checkboxes should become enabled
        self.assertEqual(self.find('input[value="all_scores"]').is_enabled(), True)
        self.assertEqual(self.find('input[value="current_scores"]').is_enabled(), True)

        # WHEN I select 'all_scores' checkbox
        self.find('input[value="all_scores"]').click()
        # THEN 'current_scores' checkbox should become selected too
        self.assertEqual(self.find('input[value="current_scores"]').is_selected(), True)

    def test_all_checkboxes_availability(self):
        # WHEN I get this page and click to 'all' checkbox
        self.find('input[value="all"]').click()
        # THEN all checkboxes should become selected
        self.assertEqual(self.find('input[name="donors"]').is_selected(), True)
