# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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
from django.contrib import auth
from django.contrib.sites.models import Site
from django.core.exceptions import MiddlewareNotUsed
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.middleware.locale import LocaleMiddleware
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.encoding import iri_to_uri
from livesettings import config_value

from .models import OrgUser


class CustomLocaleMiddleware(LocaleMiddleware):

    def process_request(self, request):
        is_i18n_pattern = self.is_language_prefix_patterns_used()
        user = auth.get_user(request)
        if is_i18n_pattern and user.is_authenticated() and user.profile.language:
            language = user.profile.language
            language_in_path = translation.get_language_from_path(request.path_info)
            if language_in_path and language != language_in_path:
                if request.META.get('QUERY_STRING', ''):
                    query = '?' + iri_to_uri(request.META['QUERY_STRING'])
                else:
                    query = ''
                full_path = '%s%s' % (request.path_info[3:], query)
                language_url = "%s://%s/%s%s" % (
                    request.is_secure() and 'https' or 'http',
                    request.get_host(), language, full_path)
                return HttpResponseRedirect(language_url)
        else:
            language = translation.get_language_from_request(request, check_path=is_i18n_pattern)

        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()


class OrguserTrackingMiddleware(object):
    """
    Mark orguser as "seen" on any request.
    NOTE: It should be placed after AuthenticationMiddleware
    """
    def process_request(self, request):
        if request.user.is_authenticated():
            for orguser in OrgUser.objects.filter(userprofile=request.user.profile, seen=False):
                # NOTE: We rely on post_save signal, hence can't use update()
                orguser.seen = True
                orguser.save()


class StaticDataInitMiddleware(object):
    """
    TODO: Remove this after upgrade to Django 1.7, use new Apps framework for initialization.

    This middleware is a hacky way to initialize default StaticPage model instances on
    server startup. It will create non-existent pages, and if content is empty, fill in
    default english content, rendering default templates.
    This middleware will remove itself from the stack, raising MiddlewareNotUsed after init.
    """
    def __init__(*args, **kwargs):
        from . import models

        registration_url = 'http://%s%s' % (
            Site.objects.get_current().domain,
            reverse('exmo2010:registration_form'))
        context = {
            'support_email': config_value('EmailServer', 'DEFAULT_SUPPORT_EMAIL'),
            'registration_url': registration_url,
        }

        pages = {
            'help': 'exmo2010/static_pages/help.html',
            'about': 'exmo2010/static_pages/about.html'}

        for page_id, template in pages.items():
            page, created = models.StaticPage.objects.get_or_create(id=page_id)
            if not page.content_en:
                with translation.override('en'):
                    page.content_en = render_to_string(template, context)
                page.save()

        models.LicenseTextFragments.objects.get_or_create(id='license')

        left, created = models.FrontPageTextFragments.objects.get_or_create(id='about_project_left')
        if created:
            left.content_ru = """
            <p style="text-align:center"><strong><span style="font-size:36px">3 710</span></strong></p>
            <p style="text-align:center">сайтов оценили за 2014 год</p>
            <div style="margin-left:20px;margin-right:20px;margin-top:25px;">
                <p><span style="font-size:14px"><strong>Измерение информационной открытости</strong></span></p>
                <p>Мы измеряем, насколько сайты соответствуют требованиям закона в процентах и граммах.</p>
            </div>
            """
            left.save()

        right, created = models.FrontPageTextFragments.objects.get_or_create(id='about_project_right')
        if created:
            right.content_ru = """
            <p style="text-align:center"><span style="font-size:36px"><strong>25%</strong></span></p>
            <p style="text-align:center">средний прирост открытости</p>
            <div style="margin-left:20px;margin-right:20px;margin-top:25px;">
                <p><span style="font-size:14px"><strong>Повышение информационной открытости</strong></span></p>
                <p>Мы консультируем по вопросам соблюдения нормативных требований к сайтам.</p>
            </div>
            """
            right.save()

        leading_expert, created = models.FrontPageTextFragments.objects.get_or_create(id='leading_expert')
        if created:
            leading_expert.content_ru = "Михаил Карягин"
            leading_expert.content_en = "Mikhail Karyagin"
            leading_expert.save()

        contact_phone, created = models.FrontPageTextFragments.objects.get_or_create(id='contact_phone')
        if created:
            contact_phone.content_ru = "+7 (812) 944-13-40"
            contact_phone.save()

        contact_email, created = models.FrontPageTextFragments.objects.get_or_create(id='contact_email')
        if created:
            contact_email.content_ru = "info@infometer.org"
            contact_email.save()

        contact_description, created = models.FrontPageTextFragments.objects.get_or_create(id='contact_description')
        if created:
            contact_description.content_ru = "Ведущий эксперт проекта"
            contact_description.content_en = "Leading expert of the project"
            contact_description.save()

        raise MiddlewareNotUsed  # remove this middleware from stack
