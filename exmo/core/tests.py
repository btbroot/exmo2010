# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013 Foundation "Institute for Information Freedom Development"
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
from django.test import TestCase
from livesettings import config_value
from nose_parameterized import parameterized

from core.mail_tests import LocmemBackendTests
from core.tasks import generate_email_message
from core.utils import urlize


class UrlizeTestCase(TestCase):
    # should convert plain urls to 'a' tags and add target='_blank'

    @parameterized.expand([
        ('<a><span>X</span>Y</a>Z', '<a target="_blank"><span>X</span>Y</a>Z'),
        ('http://ya.ru', '<a href="http://ya.ru" target="_blank">http://ya.ru</a>')
    ])
    def test_urlize(self, data, expected_result):
        self.assertEqual(urlize(data), expected_result)


class GeneratedEmailMessageTestCase(LocmemBackendTests, TestCase):
    # Scenario: Check generating email function

    @parameterized.expand([
        ('example1@email.ru', 'subject1', 'score_claim'),
        ('example2@email.ru', 'subject2', 'score_comment'),
        ('example3@email.ru', 'subject3', 'score_clarification'),
        ('example4@email.ru', 'subject4', 'certificate_order_email'),
    ])
    def test_generated_email_headers(self, to, subject, template_name):
        from_email = config_value('EmailServer', 'DEFAULT_FROM_EMAIL')
        # WHEN message is generated
        msg = generate_email_message(to, subject, template_name)
        # THEN message has expected headers
        self.assertEqual(msg.message()['To'].encode(), to)
        self.assertEqual(msg.message()['Subject'].encode(), subject)
        self.assertEqual(msg.message()['From'].encode(), from_email)
        # AND message has plaintext and html payload
        payload0 = msg.message().get_payload(0)
        self.assertMessageHasHeaders(payload0, {
            ('Content-Type', 'text/plain; charset="utf-8"'),
        })
        payload1 = msg.message().get_payload(1)
        self.assertMessageHasHeaders(payload1, {
            ('Content-Type', 'text/html; charset="utf-8"'),
        })
