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
from __future__ import unicode_literals


from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from core.test_utils import TestCase
from model_mommy import mommy

from exmo2010.models import Monitoring
from exmo2010.models.monitoring import INT


class UploadParametersCSVTest(TestCase):
    # exmo2010:monitoring_parameter_import

    # Upload parameters.

    def setUp(self):
        # GIVEN interaction monitoring
        self.monitoring = mommy.make(Monitoring, status=INT)
        # AND expert A account
        self.expertA = User.objects.create_user('expertA', 'expertA@svobodainfo.org', 'password')
        self.expertA.profile.is_expertA = True
        # AND url for csv-file importing
        self.url = reverse('exmo2010:monitoring_parameter_import', args=[self.monitoring.pk])
        # AND I am logged in as expert A
        self.client.login(username='expertA', password='password')

    def test_empty_name_param_upload(self):
        csv_data = unicode(
            # code,name,grounds,rating_procedure,notes,complete,topical,accessible,hypertext,document,image,weight
            '1,name1,grounds1,,,1,1,1,1,0,0,3\n'
            '2,name2,,rating_procedure2,notes2,1,1,1,1,0,0,3\n'
            '3,\n'   # incomplete row
            '4,name4,grounds4,rating_procedure4,notes4,1,1,1,1,0,0,3')
        f = ContentFile(csv_data.encode('utf-16'), name='temp.csv')

        # WHEN I upload csv file with incomplete third row, missing name and all columns after
        response = self.client.post(self.url, data={'paramfile': f, 'monitoring_pk': self.monitoring.pk})
        # THEN response should display error in third line
        self.assertEqual(response.context['errors'], ['row 3 (csv). Empty name'])
