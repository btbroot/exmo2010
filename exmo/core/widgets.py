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

from django import forms
from django.utils.encoding import force_text


class ModelMultiRawInput(forms.TextInput):
    def render(self, name, value, attrs=None):
        if value:
            value = ','.join([force_text(v) for v in value])
        else:
            value = ''
        return super(ModelMultiRawInput, self).render(name, value, attrs)

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        if value:
            return value.split(',')
