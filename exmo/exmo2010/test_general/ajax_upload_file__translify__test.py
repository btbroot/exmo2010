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

import json
from os.path import join

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.files import File
from django.core.urlresolvers import reverse
from mock import Mock

from core.test_utils import FileStorageTestCase


class AjaxUploadUnicodeFileTestCase(FileStorageTestCase):
    # exmo2010:ajax_upload_file

    # BUG #2369
    # Uploaded files with unicode names should get translified names.

    def setUp(self):
        # GIVEN i am logged in as experA
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        self.client.login(username='expertA', password='password')

    def test(self):
        url = reverse('exmo2010:ajax_upload_file')
        mock_file = Mock(spec=File, _size=12, read=lambda: 'some content')
        mock_file.name = u'ЫВА.doc'

        # WHEN i upload file with unicode symbols in name
        response = self.client.post(url, {'upload_file': mock_file}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # THEN response status code is 200 (OK)
        self.assertEqual(response.status_code, 200)

        # AND saved filename should get translified
        result = json.loads(response.content)
        self.assertEqual(result['saved_filename'], 'YiVA.doc')
        # AND saved file content should match uploaded file content
        saved_file = default_storage.open(join(settings.EMAIL_ATTACHMENT_UPLOAD_PATH, result['saved_filename']))
        self.assertEqual(saved_file.read(), 'some content')
