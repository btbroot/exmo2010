# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
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
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404
from django.template import loader
from django.template.response import TemplateResponse

from core.sort_headers import SortHeaders
from perm_utils import annotate_exmo_perms


def table_prepare_queryset(request, headers, queryset):
    """
    Поготовка отсортированного и отфильтрованного QS для object_list.

    """
    sort_headers = SortHeaders(request, headers)
    if sort_headers.get_order_by():
        queryset = queryset.order_by(sort_headers.get_order_by())
    queryset = queryset.filter(**sort_headers.get_filter())
    extra_context = {'headers': sort_headers.headers()}
    return queryset, extra_context


def object_list(request, queryset, paginate_by=None, page=None,
        allow_empty=True, template_name=None, template_loader=loader,
        extra_context=None, context_processors=None, template_object_name='object',
        mimetype=None):
    """
    Generic list of objects.

    Templates: ``<app_label>/<model_name>_list.html``
    Context:
        object_list
            list of objects
        is_paginated
            are the results paginated?
        results_per_page
            number of objects per page (if paginated)
        has_next
            is there a next page?
        has_previous
            is there a prev page?
        page
            the current page
        next
            the next page
        previous
            the previous page
        pages
            number of pages, total
        hits
            number of objects, total
        last_on_page
            the result number of the last of object in the
            object_list (1-indexed)
        first_on_page
            the result number of the first object in the
            object_list (1-indexed)
        page_range:
            A list of the page numbers (1-indexed).
    """
    if extra_context is None: extra_context = {}
    queryset = queryset._clone()

    if paginate_by:
        paginator = Paginator(queryset, paginate_by)

        page = request.GET.get('page')
        try:
            queryset = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            queryset = paginator.page(1)
        except EmptyPage:
            # If page is out of range, deliver last page of results.
            queryset = paginator.page(paginator.num_pages)

    context = {'%s_list' % template_object_name: annotate_exmo_perms(queryset, request.user)}
    if not allow_empty and len(queryset) == 0:
        raise Http404

    for key, value in extra_context.items():
        if callable(value):
            context[key] = value()
        else:
            context[key] = value
    if not template_name:
        model = queryset.model
        template_name = "%s/%s_list.html" % (model._meta.app_label, model._meta.object_name.lower())
    return TemplateResponse(request, template_name, context)


def table(request, headers, **kwargs):
    """
    Generic sortable table view.
    """
    kwargs['queryset'], extra_context = table_prepare_queryset(request, headers, kwargs['queryset'])
    if 'extra_context' not in kwargs:
        kwargs['extra_context'] = extra_context
    else:
        kwargs['extra_context'].update(extra_context)
    return object_list(request, **kwargs)

