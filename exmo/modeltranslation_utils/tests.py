# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2014 Foundation "Institute for Information Freedom Development"
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
from django.forms.models import modelform_factory
from core.test_utils import TestCase
from django.utils import translation
from model_mommy import mommy

from . import CurLocaleModelForm
from exmo2010.models import Monitoring, Parameter


class CurLocaleModelFormValidationTestCase(TestCase):
    """ CurLocaleModelForm should set "required" flag for non-blank translatable modelfields """

    def test_validation(self):
        translation.activate('en')
        monitoring = mommy.make(Monitoring)
        ParamForm = modelform_factory(model=Parameter, form=CurLocaleModelForm)
        data = dict(code='1', monitoring=monitoring.pk, weight=1)

        # Data missing required for current locale field "name_en" should be invalid
        self.assertFalse(ParamForm(dict(data)).is_valid())
        self.assertFalse(ParamForm(dict(data, name='lol')).is_valid())
        self.assertFalse(ParamForm(dict(data, name_ru='lol')).is_valid())

        # Valid data, with required "name_en" field
        self.assertTrue(ParamForm(dict(data, name_en='lol')).is_valid())
