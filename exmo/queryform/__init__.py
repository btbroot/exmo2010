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
import operator

from django import forms
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.forms.forms import DeclarativeFieldsMetaclass
from django.utils import six


class FormOptions(object):
    def __init__(self, options=None):
        self.filters = getattr(options, 'filters', None)
        self.distinct = getattr(options, 'distinct', False)


class DeclarativeMetaclass(DeclarativeFieldsMetaclass):
    def __new__(mcs, *args):
        new_class = super(DeclarativeMetaclass, mcs).__new__(mcs, *args)
        new_class._meta = FormOptions(getattr(new_class, 'Meta', None))

        return new_class


class QueryForm(six.with_metaclass(DeclarativeMetaclass, forms.BaseForm)):

    def __init__(self, data=None, objects_per_page=None, **kwargs):
        super(QueryForm, self).__init__(data, **kwargs)
        self.objects_per_page = objects_per_page

    def get_filter(self):
        opts = self._meta
        result = []
        for field_name, value in self.cleaned_data.items():
            q_list = []
            if value:
                q_filter = opts.filters.get(field_name, None)
                if not isinstance(q_filter, (list, tuple)):
                    q_filter = [q_filter]
                q_list = [Q(**{q: value}) for q in q_filter]

            q_filter = reduce(operator.or_, q_list) if q_list else None

            if q_filter:
                result.append(q_filter)

        return reduce(operator.and_, result) if result else None

    def paginate(self, queryset):
        paginator = Paginator(queryset, self.objects_per_page)

        page = self.data.get('page')
        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            queryset = paginator.page(1)
        except EmptyPage:
            # If page is out of range, deliver last page of results.
            queryset = paginator.page(paginator.num_pages)

        return queryset

    def apply(self, queryset):
        query = self.get_filter()
        if query:
            if self._meta.distinct:
                queryset = queryset.distinct()
            queryset = queryset.filter(query)

        if self.objects_per_page:
            queryset = self.paginate(queryset)

        return queryset
