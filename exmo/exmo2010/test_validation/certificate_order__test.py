# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2016 IRSI LTD
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
from mock import Mock
from model_mommy import mommy
from nose_parameterized import parameterized

from core.test_utils import OptimizedTestCase
from exmo2010.models import Organization, PUB, OrgUser, Score, Parameter, Task
from exmo2010.views.views import CertificateOrderView


class CertificateOrderFormValidationTestCase(OptimizedTestCase):
    # TODO: move this testcase to *validation* tests directory

    # exmo2010:certificate_order

    # CertificateOrderForm should properly validate input data

    fields = 'addressee delivery_method name email for_whom zip_code address'.split()

    @classmethod
    def setUpClass(cls):
        super(CertificateOrderFormValidationTestCase, cls).setUpClass()
        cls.view = staticmethod(CertificateOrderView.as_view())

        # GIVEN organization and approved task in PUBLISHED monitoring
        org = mommy.make(Organization, monitoring__status=PUB)
        cls.task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
        # AND parameter with score
        param = mommy.make(Parameter, monitoring=org.monitoring, weight=1)
        mommy.make(Score, task=cls.task, parameter=param, found=1)
        # AND organization representative
        cls.orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        cls.orguser.groups.add(Group.objects.get(name=cls.orguser.profile.organization_group))
        mommy.make(OrgUser, organization=org, userprofile=cls.orguser.profile)

    def mock_request(self, values):
        data = dict(zip(self.fields, values), task_id=self.task.pk, rating_type='all')
        return Mock(user=self.orguser, method='POST', is_ajax=lambda: False, POST=data, GET={})

    @parameterized.expand([
        # Email Delivery
        ('org', 'email', '', 'test@mail.com', '', '', ''),
        ('user', 'email', 'name', 'test@mail.com', '', '', ''),
        # Postal Delivery
        # NOTE: temporarily disabled in code
        #('org', 'post', '', '', 'for me', '123456', 'address'),
        #('user', 'post', 'name', '', 'for me', '123456', 'address'),
    ])
    def test_valid_form(self, *values):
        # WHEN orguser submits request with valid data
        response = self.view(self.mock_request(values))
        # THEN form validation should succeed
        self.assertEqual(response.context_data['form'].is_valid(), True)

    @parameterized.expand([
        # Email Delivery
        ('org', 'email', '', '', '', '', ''),  # missing email
        # Postal Delivery
        # NOTE: temporarily disabled in code
        #('org', 'post', '', '', 'for me', '123456', ''),   # missing address
        #('org', 'post', '', '', 'for me', '', 'address'),  # missing zip_code
        #('org', 'post', '', '', '', '123456', 'address'),  # missing for_whom
        #('org', 'post', '', '', 'for me', '1234', 'address'),  # malformed zip_code
        #('org', 'post', '', '', 'for me', 'text', 'address'),
    ])
    def test_invalid_form(self, *values):
        # WHEN orguser submits request with invalid data
        response = self.view(self.mock_request(values))
        # THEN form validation should fail
        self.assertEqual(response.context_data['form'].is_valid(), False)
