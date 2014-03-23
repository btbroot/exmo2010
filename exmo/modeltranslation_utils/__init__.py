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

from django import forms
from django.utils.translation import get_language
from modeltranslation.fields import TranslationField
from modeltranslation.translator import translator


class CurLocaleModelForm(forms.ModelForm):
    """
    Modelform that will automatically exclude all translated fields except felds for
    current activated language.
    """
    def __init__(self, *args, **kwargs):
        super(CurLocaleModelForm, self).__init__(*args, **kwargs)

        # trans_fields will contain dict from original field name to localized bound
        # formfield for current locale.
        # This is useful in templates to render localized field by original name without
        # locale suffix. For example to render localized name field in template you can write:
        #    {{form.trans_fields.name}}
        # if current locale is 'en' it is equivalent to:
        #    {{form.name_en}}
        self.trans_fields = {}

        model_trans_fields = translator.get_options_for_model(self._meta.model).fields
        lang = get_language()
        for f in self._meta.model._meta.fields:
            if f.name not in self.fields:
                continue
            if f.name in model_trans_fields:
                del self.fields[f.name]  # Delete original unlocalized fields
            elif isinstance(f, TranslationField):
                if not f.name.endswith('_' + lang):
                    # Delete localized field for other language
                    del self.fields[f.name]
                else:
                    # Set trans_fields mapping from original field name to this field
                    self.trans_fields[f.translated_field.name] = self[f.name]

                    if not f.translated_field.blank:
                        # Original modelfield has blank=False attribute, we should set "required" flag on
                        # localized formfield for current language.
                        self.fields[f.name].required = True

    def _get_validation_exclusions(self):
        # Always include trans_fields in validation checks
        exclude = super(CurLocaleModelForm, self)._get_validation_exclusions()
        return list(set(exclude) - set(self.trans_fields))
