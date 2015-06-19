# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
# Copyright 2015 IRSI LTD
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

from modeltranslation.translator import translator, TranslationOptions

from . import models


def register(model):
    def wrapper(cls):
        translator.register(model, cls)
        return cls
    return wrapper


@register(models.Monitoring)
class MonitoringTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(models.Parameter)
class ParameterTranslationOptions(TranslationOptions):
    fields = ('name', 'grounds', 'rating_procedure', 'notes')


@register(models.Organization)
class OrganizationTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(models.StaticPage)
class StaticPageTranslationOptions(TranslationOptions):
    fields = ('description', 'content')


@register(models.LicenseTextFragments)
class LicenseTextFragmentsTranslationOptions(TranslationOptions):
    fields = ('page_footer', 'csv_footer')


@register(models.FrontPageTextFragments)
class FrontPageFragmentsTranslationOptions(TranslationOptions):
    fields = ('content',)
