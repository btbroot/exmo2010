# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014-2015 IRSI LTD
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

from datetime import datetime

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from core.test_utils import TestCase
from django.utils import translation
from mock import MagicMock, Mock
from model_mommy import mommy
from nose_parameterized import parameterized

from .middleware import CustomLocaleMiddleware
from .models import (Group, Monitoring, ObserversGroup, Organization, Parameter,
                     Score, PhonesField, Task, UserProfile, MONITORING_PUBLISHED)
from .templatetags.exmo2010_filters import linkify
from .views import CertificateOrderView, ckeditor_upload, org_url_re
from core.test_utils import OptimizedTestCase, TranslationTestCase
from core.utils import get_named_patterns, workday_count


class TestPhonesFieldValidation(TestCase):
    """ PhonesField should accept only valid input """

    def test_phones_field(self):
        field = PhonesField()
        # All combinations of delimeters should be properly stripped
        # Spaces should only be stripped on edges
        self.assertEqual(field.to_python('\t,\r1-2345\n   1 23 45,\t \n12345,\n\r, '), '1-23-45, 1 23 45, 1-23-45')
        self.assertEqual(field.to_python("+7(868)876-45-56, +7(868)876-45-56"), "+7(868)876-45-56, +7(868)876-45-56")


class FeedbackEmailTestCase(TestCase):
    """ When feedback form is submitted, two emails should be sent - to staff and back to submitter """

    @parameterized.expand(settings.LANGUAGES)
    def test_feedback_email(self, language_code, language_name):
        with translation.override(language_code):
            response = self.client.post(reverse('exmo2010:feedback_form'), {'email': 'tst@ya.ru', 'comment': '123'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(mail.outbox), 2)


class NegativeParamMonitoringRatingTestCase(TestCase):
    # Parameters with negative weight SHOULD affect openness

    def setUp(self):
        # GIVEN monitoring with parameter that has negative weight
        self.monitoring = mommy.make(Monitoring, openness_expression__code=8)
        # AND parameter with weight -1
        self.parameter = mommy.make(Parameter, monitoring=self.monitoring, weight=-1, exclude=[],
                                    complete=1, topical=1, accessible=1, hypertext=1, document=1, image=1)
        # AND parameter with weight 2
        self.parameter2 = mommy.make(Parameter, monitoring=self.monitoring, weight=2, exclude=[],
                                    complete=1, topical=1, accessible=1, hypertext=1, document=1, image=1)
        # AND organization, approved task
        org = mommy.make(Organization, monitoring=self.monitoring)
        task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)

        # AND equal scores for 2 parameters
        kwargs = dict(found=1, complete=3, topical=3, accessible=3, hypertext=1, document=1, image=1)
        mommy.make(Score, task=task, parameter=self.parameter, **kwargs)
        mommy.make(Score, task=task, parameter=self.parameter2, **kwargs)

    def test_rating_with_negative_param(self):
        # WHEN rating is calculated for monitoring with parameter that has negative weight
        task = self.monitoring.rating()[0]
        # THEN task openness is 50%
        self.assertEqual(task.task_openness, 50)


class CanonicalViewKwargsTestCase(TestCase):
    # Url patterns and views should use and accept only canonical kwargs

    test_patterns = {p.name: p for p in get_named_patterns() if p._full_name.startswith('exmo2010:')}

    canonical_kwargs = {
        'monitoring_pk',
        'score_pk',
        'parameter_pk',
        'task_pk',
        'org_pk',
        'clarification_pk',
        'claim_pk',
        'obs_group_pk',
        'monitoring_status',  # for monitorings_list
        'activation_key',     # for registration_activate
        'user_pk',            # for password_reset_confirm
        'token',              # for password_reset_confirm
        'report_type',        # for monitoring_report_*
        'print_report_type',  # for task_scores
    }

    @parameterized.expand(test_patterns)
    def test_urlpattern(self, name):
        pat = self.test_patterns[name]

        if pat.regex.groups > len(pat.regex.groupindex):
            raise Exception(
                'Urlpattern ("%s", "%s") uses positional args and can\'t be reversed for this test. '
                'It should be modified to use only kwargs or excluded from this test and tested explicitly'
                    % (pat.regex.pattern, pat.name))
        unknown_kwargs = set(pat.regex.groupindex) - self.canonical_kwargs
        if unknown_kwargs:
            raise Exception(
                'Urlpattern ("%s", "%s") uses unknown kwargs and can\'t be reversed for this test. '
                'These kwargs should be added to this test\'s auto_pattern_kwargs in setUp'
                    % (pat.regex.pattern, pat.name))


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
        org = mommy.make(Organization, monitoring__status=MONITORING_PUBLISHED)
        cls.task = mommy.make(Task, organization=org, status=Task.TASK_APPROVED)
        # AND parameter with score
        param = mommy.make(Parameter, monitoring=org.monitoring, weight=1)
        mommy.make(Score, task=cls.task, parameter=param, found=1)
        # AND organization representative
        cls.orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        cls.orguser.groups.add(Group.objects.get(name=cls.orguser.profile.organization_group))
        cls.orguser.profile.organization = [org]

    def mock_request(self, values):
        data = dict(zip(self.fields, values), task_id=self.task.pk, rating_type='all')
        return Mock(user=self.orguser, method='POST', is_ajax=lambda: False, POST=data, GET={})

    @parameterized.expand([
        # Email Delivery
        ('org', 'email', '', 'test@mail.com', '', '', ''),
        ('user', 'email', 'name', 'test@mail.com', '', '', ''),
        # Postal Delivery
        ('org', 'post', '', '', 'for me', '123456', 'address'),
        ('user', 'post', 'name', '', 'for me', '123456', 'address'),
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
        ('org', 'post', '', '', 'for me', '123456', ''),   # missing address
        ('org', 'post', '', '', 'for me', '', 'address'),  # missing zip_code
        ('org', 'post', '', '', '', '123456', 'address'),  # missing for_whom
        ('org', 'post', '', '', 'for me', '1234', 'address'),  # malformed zip_code
        ('org', 'post', '', '', 'for me', 'text', 'address'),
    ])
    def test_invalid_form(self, *values):
        # WHEN orguser submits request with invalid data
        response = self.view(self.mock_request(values))
        # THEN form validation should fail
        self.assertEqual(response.context_data['form'].is_valid(), False)


class CertificateOpennessValuesByTypeTestCase(TestCase):
    # SHOULD display correct openness value of requested rating type

    def setUp(self):
        # GIVEN published monitoring
        monitoring = mommy.make(Monitoring, status=MONITORING_PUBLISHED)
        # AND organization
        organization = mommy.make(Organization, name='org1', monitoring=monitoring)
        # AND approved task
        self.task = mommy.make(Task, organization=organization, status=Task.TASK_APPROVED)
        # AND normative parameter
        kwargs = dict(complete=1, topical=1, accessible=1, hypertext=1, document=1, image=1)
        parameter1 = mommy.make(Parameter, monitoring=monitoring, weight=1, exclude=[], npa=True, **kwargs)
        # AND recommendatory parameter
        parameter2 = mommy.make(Parameter, monitoring=monitoring, weight=2, exclude=[], npa=False, **kwargs)
        # AND not equal scores for 2 parameters
        kwargs1 = dict(found=1, complete=2, topical=2, accessible=3, hypertext=1, document=1, image=0)
        kwargs2 = dict(found=1, complete=3, topical=3, accessible=2, hypertext=0, document=1, image=1)
        mommy.make(Score, task=self.task, parameter=parameter1, **kwargs1)
        mommy.make(Score, task=self.task, parameter=parameter2, **kwargs2)
        # AND organization representative account
        org = User.objects.create_user('org', 'org@svobodainfo.org', 'password')
        org.groups.add(Group.objects.get(name=org.profile.organization_group))
        org.profile.organization.add(organization)
        # AND I am logged in as organization representative
        self.client.login(username='org', password='password')

    @parameterized.expand([
        ('all', 26.125),
        ('npa', 40.375),
        ('other', 19.0),
    ])
    def test_openness(self, rating_type, expected_openness):
        # WHEN I get certificate page with specific rating
        url = reverse('exmo2010:certificate_order')
        response = self.client.get(url, {'rating_type': rating_type})
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND context should contain expected openness value
        self.assertEqual(response.context['view'].tasks[self.task.pk].task_openness, expected_openness)


class CertificateOrgsFilterByRatingTypeTestCase(TestCase):
    # SHOULD display only organizations with requested rating type

    def setUp(self):
        # GIVEN published monitoring with 1 npa parameter, score and 1 organization
        org_npa = mommy.make(Organization, name='npa', monitoring__status=MONITORING_PUBLISHED)
        parameter_npa = mommy.make(Parameter, monitoring=org_npa.monitoring, weight=1, npa=True)
        mommy.make(Score, task__status=Task.TASK_APPROVED, task__organization=org_npa, parameter=parameter_npa, found=1)

        # AND published monitoring with 1 non-npa parameter, score and 1 organization
        # NOTE: Currently we treat this monitoring params as of "undefined" type
        # This monitoring should only be visible when "all" rating type is chosen
        org_non_npa = mommy.make(Organization, name='non-npa', monitoring__status=MONITORING_PUBLISHED)
        parameter_non_npa = mommy.make(Parameter, monitoring=org_non_npa.monitoring, weight=1, npa=False)
        mommy.make(Score, task__status=Task.TASK_APPROVED, task__organization=org_non_npa, parameter=parameter_non_npa, found=1)

        # AND published monitoring with 2 parameters (npa and non-npa), 2 scores and 1 organization
        org_all = mommy.make(Organization, name='all', monitoring__status=MONITORING_PUBLISHED)
        parameter_all_npa = mommy.make(Parameter, monitoring=org_all.monitoring, weight=1, npa=True)
        parameter_all_non_npa = mommy.make(Parameter, monitoring=org_all.monitoring, weight=1, npa=False)
        task = mommy.make(Task, organization=org_all, status=Task.TASK_APPROVED)
        mommy.make(Score, task=task, parameter=parameter_all_npa, found=1)
        mommy.make(Score, task=task, parameter=parameter_all_non_npa, found=1)

        # AND organization representative account
        orguser = User.objects.create_user('orguser', 'org@svobodainfo.org', 'password')
        orguser.groups.add(Group.objects.get(name=orguser.profile.organization_group))
        orguser.profile.organization = [org_npa, org_non_npa, org_all]
        # AND I am logged in as organization representative
        self.client.login(username='orguser', password='password')

    @parameterized.expand([
        ('all', ['all', 'npa', 'non-npa']),
        ('npa', ['all', 'npa']),
        ('other', ['all']),
    ])
    def test_openness(self, rating_type, expected_orgs):
        # WHEN I get certificate page with specific rating
        response = self.client.get(reverse('exmo2010:certificate_order'), {'rating_type': rating_type})
        # THEN response status_code should be 200 (OK)
        self.assertEqual(response.status_code, 200)
        # AND context should contain only organizations for requested rating type
        orgs = [t.organization.name for t in response.context['view'].tasks.values()]
        self.assertEqual(set(orgs), set(expected_orgs))


class ChangeLanguageViewTestCase(TranslationTestCase):
    # Scenario: Change language view tests

    def setUp(self):
        self.url = reverse('exmo2010:change_language')
        # GIVEN registered user without any permissions
        self.user = User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND this user has not language preference
        self.user.profile.language = ''
        self.user.profile.save()

    @parameterized.expand(settings.LANGUAGES)
    def test_user_change_language(self, language_code, language_name):
        # WHEN I am logged in as user
        self.client.login(username='user', password='password')
        # AND I submit change language form
        data = {
            'language': language_code,
        }
        self.client.post(self.url, data)
        # THEN user profile settings should contain posted language code
        user_profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(user_profile.language, language_code)


class CustomLocaleMiddlewareTest(TranslationTestCase):
    # Scenario: Custom locale middleware tests

    def setUp(self):
        # GIVEN custom locale middleware
        self.middleware = CustomLocaleMiddleware()
        # AND registered user without any permissions
        self.user = User.objects.create_user('user', 'user@svobodainfo.org', 'password')
        # AND request object for authentication user
        self.request = MagicMock()
        self.request.get_host = lambda: 'test'
        self.request.is_secure = lambda: False
        self.request.META = {}
        self.request.session = {
            '_auth_user_id': self.user.id,
            '_auth_user_backend': 'django.contrib.auth.backends.ModelBackend',
        }

    @parameterized.expand(settings.LANGUAGES)
    def test_process_request_language_not_in_path(self, language_code, language_name):
        # WHEN path hasn't a language
        self.request.path_info = '/'
        # AND user has language preference
        self.user.profile.language = language_code
        self.user.profile.save()
        # THEN middleware should return nothing
        self.assertEqual(self.middleware.process_request(self.request), None)
        # AND project language should be exactly as in user preference
        self.assertEqual(translation.get_language(), language_code)

    @parameterized.expand(settings.LANGUAGES)
    def test_process_request_language_in_path_and_language_equal_language_in_path(self, language_code, language_name):
        # WHEN path has a language
        self.request.path_info = '/%s/' % language_code
        # AND user has the same language in preference
        self.user.profile.language = language_code
        self.user.profile.save()
        # THEN middleware should return nothing
        self.assertEqual(self.middleware.process_request(self.request), None)
        # AND project language should be exactly as in user preference
        self.assertEqual(translation.get_language(), language_code)

    def test_process_request_language_in_path_and_language_not_equal_language_in_path(self):
        # WHEN path has a language
        self.request.path_info = '/ka/'
        # AND user has another language preference
        self.user.profile.language = 'ru'
        self.user.profile.save()
        # THEN middleware should return HttpResponseRedirect-object
        response = self.middleware.process_request(self.request)
        self.assertIsInstance(response, HttpResponseRedirect)
        # AND response should have expected url to redirect
        self.assertEqual(response['Location'], 'http://test/ru/')


class CKEditorImageUploadAccessTestCase(OptimizedTestCase):
    # ckeditor_upload

    # Should forbid anonymous or unprivileged user to upload files

    @classmethod
    def setUpClass(cls):
        super(CKEditorImageUploadAccessTestCase, cls).setUpClass()

        cls.users = {}
        # GIVEN monitoring with organization
        cls.monitoring = mommy.make(Monitoring)
        organization = mommy.make(Organization, monitoring=cls.monitoring)
        # AND anonymous user
        cls.users['anonymous'] = AnonymousUser()
        # AND user without any permissions
        cls.users['user'] = User.objects.create_user('user', 'usr@svobodainfo.org', 'password')
        # AND superuser
        cls.users['admin'] = User.objects.create_superuser('admin', 'usr@svobodainfo.org', 'password')
        # AND expert B
        expertB = User.objects.create_user('expertB', 'usr@svobodainfo.org', 'password')
        expertB.profile.is_expertB = True
        cls.users['expertB'] = expertB
        # AND expert A
        expertA = User.objects.create_user('expertA', 'usr@svobodainfo.org', 'password')
        expertA.profile.is_expertA = True
        cls.users['expertA'] = expertA
        # AND organization representative
        orguser = User.objects.create_user('orguser', 'usr@svobodainfo.org', 'password')
        orguser.profile.organization = [organization]
        cls.users['orguser'] = orguser
        # AND translator
        translator = User.objects.create_user('translator', 'usr@svobodainfo.org', 'password')
        translator.profile.is_translator = True
        cls.users['translator'] = translator
        # AND observer user
        observer = User.objects.create_user('observer', 'usr@svobodainfo.org', 'password')
        # AND observers group for monitoring
        obs_group = mommy.make(ObserversGroup, monitoring=cls.monitoring)
        obs_group.organizations = [organization]
        obs_group.users = [observer]
        cls.users['observer'] = observer
        # AND url
        cls.url = reverse('ckeditor_upload')

    def test_redirect_get_anonymous(self):
        # WHEN anonymous user get upload url
        request = MagicMock(user=self.users['anonymous'], method='GET')
        request.get_full_path.return_value = self.url
        response = ckeditor_upload(request)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertEqual(response['Location'], '{}?next={}'.format(settings.LOGIN_URL, self.url))

    def test_redirect_post_anonymous(self):
        # WHEN anonymous user upload file
        request = MagicMock(user=self.users['anonymous'], method='POST', FILES={'upload': Mock()})
        request.get_full_path.return_value = self.url
        response = ckeditor_upload(request)
        # THEN response status_code should be 302 (redirect)
        self.assertEqual(response.status_code, 302)
        # AND response redirects to login page
        self.assertEqual(response['Location'], '{}?next={}'.format(settings.LOGIN_URL, self.url))

    @parameterized.expand(zip(['orguser', 'observer', 'user']))
    def test_forbid_post_comment(self, username, *args):
        # WHEN unprivileged user upload file
        request = Mock(user=self.users[username], method='POST', FILES={'upload': Mock()})
        # THEN response should raise PermissionDenied exception
        self.assertRaises(PermissionDenied, ckeditor_upload, request)

    @parameterized.expand(zip(['admin', 'expertA', 'expertB', 'translator']))
    def test_allow_post(self, username, *args):
        # WHEN privileged user upload file
        request = MagicMock(user=self.users[username], method='POST', FILES={'upload': Mock()})
        # THEN response status_code should be 200 (OK)
        self.assertEqual(ckeditor_upload(request).status_code, 200)


class LinkifyTestCase(TestCase):
    # Should convert plain urls to anchor tags, leaving existing anchors untouched.
    # Should add target="_blank" to anchor tags.
    # Should truncate urls longer than 70 characters.

    @parameterized.expand([
        ('<a><span>X</span>Y</a>Z', '<a><span>X</span>Y</a>Z'),
        ('text test.ru text', 'text <a target="_blank" rel="nofollow" href="http://test.ru">test.ru</a> text'),
        ('http://test.ru', '<a target="_blank" rel="nofollow" href="http://test.ru">http://test.ru</a>'),
        ('<p>http://test.ru/?code=J6VLRH&email=org5%40test.ru</p>',
         '<p><a target="_blank" rel="nofollow" href="http://test.ru/?code=J6VLRH&amp;email=org5%40test.ru">'
         'http://test.ru/?code=J6VLRH&amp;email=org5%40test.ru</a></p>'),
        ('<a href="http://test.ru/"><span>X</span>Y</a>Z',
         '<a target="_blank" rel="nofollow" href="http://test.ru/"><span>X</span>Y</a>Z'),
        ('text &lt;h2&gt;TTT&lt;/h2&gt; text', 'text &lt;h2&gt;TTT&lt;/h2&gt; text'),
        ('text &lt;h2&gt;TTT&lt;/h2&gt; text <a href="http://test.ru/"><span>X</span>Y</a> text',
         'text &lt;h2&gt;TTT&lt;/h2&gt; text <a target="_blank" rel="nofollow" href="http://test.ru/">'
         '<span>X</span>Y</a> text'),
        ('https://www.google.ru/webhp?ion=1&espv=2&ie=UTF-8#newwindow=1&q=%D1%82%D0%B5%D1%81%D1%82',
         '<a target="_blank" rel="nofollow" href="https://www.google.ru/webhp?'
         'ion=1&amp;espv=2&amp;ie=UTF-8#newwindow=1&amp;q=%D1%82%D0%B5%D1%81%D1%82">'
         'https://www.google.ru/webhp?ion=1&amp;espv=2&amp;ie=UTF-8#newwindow=1&amp;q=%D1...</a>'),
    ])
    def test_linkify(self, data, expected_result):
        self.assertEqual(BeautifulSoup(linkify(data)), BeautifulSoup(expected_result))


class WorkdayCountTestCase(TestCase):
    # Should calculate number of days between two dates, excluding weekends.

    @parameterized.expand([
        # BUG 2178. Thursday evening to next Thursday morning, should ignore hours, use date only.
        ('2014.08.07 18:31', '2014.08.14 10:08', 5),

        ('2014.08.08 18:31', '2014.08.14 00:00', 4),   # Friday to Thursday, 2 weekends
        ('2014.08.08 00:00', '2014.08.08 00:00', 0),   # same day, zero hours
        ('2014.08.08 17:14', '2014.08.08 18:10', 0),   # same day

        ('2014.08.09 18:31', '2014.08.11 00:00', 0),   # Saturday to Monday -> same day
        ('2014.08.10 18:31', '2014.08.11 00:00', 0),   # Sunday to Monday -> same day

        ('2014.08.08 17:14', '2014.08.09 18:10', 0),   # Friday to Saturday -> same day
        ('2014.08.08 17:14', '2014.08.10 18:10', 0),   # Friday to Sunday -> same day
        ('2014.08.08 17:14', '2014.08.11 14:05', 1),   # Friday to Monday
    ])
    def test_workday_count(self, start, end, expected_result):
        fmt = '%Y.%m.%d %H:%M'
        result = workday_count(datetime.strptime(start, fmt), datetime.strptime(end, fmt))
        self.assertEqual(result, expected_result)


class IndexFindScoreRegexTestCase(TestCase):
    # exmo2010:ajax_index_find_score

    # Regular expression should match only valid url provided via input form.

    @parameterized.expand([
        ('http://www.123.ru/', '123.ru'),
        ('https://www.123.ru/', '123.ru'),
        ('123.ru/456', '123.ru'),
        ('www.123.ru/&q=zxc', '123.ru'),
        ('http://www.мвд.рф/&q=zxc', 'мвд.рф'),
    ])
    def test_valid(self, input, expected):
        self.assertEqual(org_url_re.match(input).group('base_url'), expected)

    @parameterized.expand([
        ('http:www.123.ru/', ),
        ('123', ),
        ('qwe', ),
        ('.www.123/&q=zxc', ),
        ('/.мвд.рф/', ),
    ])
    def test_invalid(self, input):
        self.assertEqual(org_url_re.match(input), None)
