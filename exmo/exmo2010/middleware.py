# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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


class CustomLocaleMiddleware(LocaleMiddleware):

    def process_request(self, request):
        is_i18n_pattern = self.is_language_prefix_patterns_used()
        user = auth.get_user(request)
        if is_i18n_pattern and user.is_authenticated() and user.profile.language:
            language = user.profile.language
            language_in_path = translation.get_language_from_path(request.path_info)
            if language_in_path and language != language_in_path:
                full_path = '%s%s' % (request.path_info[3:], request.META.get('QUERY_STRING', '') and
                                     ('?' + iri_to_uri(request.META.get('QUERY_STRING', ''))) or '')
                language_url = "%s://%s/%s%s" % (
                    request.is_secure() and 'https' or 'http',
                    request.get_host(), language, full_path)
                return HttpResponseRedirect(language_url)
        else:
            language = translation.get_language_from_request(request, check_path=is_i18n_pattern)

        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()


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

        raise MiddlewareNotUsed  # remove this middleware from stack
