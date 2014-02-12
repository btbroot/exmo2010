# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
from django.forms import DateInput
from tagging.fields import TagField as TagField_orig


class TagField(TagField_orig):
    """
    A "special" character field that actually works as a relationship to tags
    "under the hood". This exposes a space-separated string of tags, but does
    the splitting/reordering/etc. under the hood.

    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 255)
        kwargs['blank'] = kwargs.get('blank', True)
        super(TagField, self).__init__(*args, **kwargs)
        self.validators = []  # hack. but nothing to validate

    def get_internal_type(self):
        return 'TextField'


try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["^core\.fields\.TagField"])
except ImportError:
    pass


# TODO: Remove this class after upgrade to Django 1.6. To enable localization for fields,
# use the localized_fields attribute on the Meta class.
class LocalizeDateInput(DateInput):
    """
    This class is a hacky way to enable localization for date fields in a ModelForm.

    """
    is_localized = True
