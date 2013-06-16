# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404, HttpResponse
from django.template import loader, RequestContext
from django.utils import translation
from django.utils.functional import wraps

from core.sort_headers import SortHeaders
from exmo2010.models import Parameter, Task, UserProfile


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
        paginator = Paginator(queryset, paginate_by, allow_empty_first_page=allow_empty)
        if not page:
            page = request.GET.get('page', 1)
        try:
            page_number = int(page)
        except ValueError:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                # Page is not 'last', nor can it be converted to an int.
                raise Http404
        try:
            page_obj = paginator.page(page_number)
        except InvalidPage:
            raise Http404
        c = RequestContext(request, {
            '%s_list' % template_object_name: page_obj.object_list,
            'paginator': paginator,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),

            # Legacy template context stuff. New templates should use page_obj
            # to access this instead.
            'results_per_page': paginator.per_page,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'page': page_obj.number,
            'next': page_obj.next_page_number(),
            'previous': page_obj.previous_page_number(),
            'first_on_page': page_obj.start_index(),
            'last_on_page': page_obj.end_index(),
            'pages': paginator.num_pages,
            'hits': paginator.count,
            'page_range': paginator.page_range,
        }, context_processors)
    else:
        c = RequestContext(request, {
            '%s_list' % template_object_name: queryset,
            'paginator': None,
            'page_obj': None,
            'is_paginated': False,
        }, context_processors)
        if not allow_empty and len(queryset) == 0:
            raise Http404
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    if not template_name:
        model = queryset.model
        template_name = "%s/%s_list.html" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    return HttpResponse(t.render(c), mimetype=mimetype)


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


def rating(monitoring, parameters=None, rating_type=None):
    """
    Генерация ретинга для мониторинга по выбранным параметрам
    Вернет tuple из отсортированного списка объектов рейинга
    и словаря средних значений Кид.

    """
    #sample extra for select
    extra_select = "count(*)"
    #get task from monitoring for valid sql
    generic_task_qs = Task.objects.filter(organization__monitoring=monitoring)
    if generic_task_qs.exists():
        extra_select = generic_task_qs[0]._sql_openness(parameters)

    tasks = Task.approved_tasks.filter(organization__monitoring=monitoring)
    total_tasks = tasks.count()

    if parameters and rating_type == 'user':
        params_list = Parameter.objects.filter(pk__in=parameters)
        non_relevant = set(params_list[0].exclude.all())
        for item in params_list[1:]:
            non_relevant &= set(item.exclude.all())

        tasks = tasks.exclude(organization__in=list(non_relevant))

    object_list = [
        {
            'task': task,
            'openness': task.__task_openness or 0,
            'openness_first': task.openness_first,
        } for task in tasks
        .extra(select={'__task_openness': extra_select})
        .order_by('-__task_openness')
    ]

    place = 1
    avg = {
        'openness': 0,
        'openness_first': 0,
        'total_tasks': total_tasks,
    }
    max_rating = 0
    if object_list:
        max_rating = object_list[0]['openness']
        avg['openness'] = sum([t['openness'] for t in object_list]) / len(object_list)
        avg['openness_first'] = sum([t['openness_first'] for t in object_list]) / len(object_list)
    rating_list = []
    place_count = {}
    for rating_object in object_list:
        if rating_object['openness'] < max_rating:
            place += 1
            max_rating = rating_object['openness']
        try:
            place_count[place] += 1
        except KeyError:
            place_count[place] = 1
        rating_object['place'] = place
        rating_list.append(rating_object)

    rating_list_final = []
    for rating_object in rating_list:
        rating_object['place_count'] = place_count[rating_object['place']]
        rating_list_final.append(rating_object)
    return rating_list_final, avg


def get_experts():
    """
    Возвращает пользователей из групп expertA и expertB_manager.

    """
    return User.objects.filter(groups__name__in=[UserProfile.expertA_group, UserProfile.expertB_manager_group],
                               is_active=True,
                               email__isnull=False)\
        .exclude(email__exact='').distinct()


def use_locale(func):
    """
    Decorator for tasks with respect to site's current language.
    e.g.:
        @task
        @use_locale
        def my_task(**kwargs):
            pass

    """
    def wrapper(*args, **kwargs):
        try:
            lang = settings.LANGUAGE_CODE
        except AttributeError:
            lang = None
        language = kwargs.pop('language', lang)
        prev_language = translation.get_language()
        if language:
            translation.activate(language)
        try:
            return func(*args, **kwargs)
        finally:
            translation.activate(prev_language)

    wrapper.__doc__ = func.__doc__
    wrapper.__name__ = func.__name__
    wrapper.__module__ = func.__module__
    return wraps(func)(wrapper)
