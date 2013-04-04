# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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

"""
Модуль помощников для вью
"""

from django.http import Http404
from django.views.generic.list_detail import object_list

from exmo2010.sort_headers import SortHeaders
from exmo2010.models import Task, Parameter
from exmo2010.forms import ParameterDynForm


def table_prepare_queryset(request, headers, queryset):
    """
    Поготовка отсортированного и отфильтрованного QS для object_list
    """
    sort_headers = SortHeaders(request, headers)
    if sort_headers.get_order_by():
        queryset = queryset.order_by(sort_headers.get_order_by())
    queryset = queryset.filter(**sort_headers.get_filter())
    extra_context = {'headers': sort_headers.headers(),}
    return queryset, extra_context


def table(request, headers, **kwargs):
    """Generic sortable table view"""
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
    и словаря средних значений Кид
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


def rating_type_parameter(request, monitoring, has_npa=False):
    """
    Функция подготовки списка параметров и формы выбора параметров
    """
    if has_npa:
        rating_type_list = ('all', 'npa', 'user', 'other')
    else:
        rating_type_list = ('all', 'user')
    rating_type = request.GET.get('type', 'all')
    if rating_type not in rating_type_list:
        raise Http404

    form = ParameterDynForm(monitoring=monitoring)
    parameter_list = []
    if rating_type == 'npa':
        parameter_list = Parameter.objects.filter(
            monitoring=monitoring,
            npa=True,
            )
    elif rating_type == 'other':
        parameter_list = Parameter.objects.filter(
            monitoring=monitoring,
            npa=False,
        )
    elif rating_type == 'user':
        form = ParameterDynForm(request.GET, monitoring=monitoring)
        for parameter in Parameter.objects.filter(monitoring=monitoring):
            if request.GET.get('parameter_%d' % parameter.pk):
                parameter_list.append(parameter.pk)

    return rating_type, parameter_list, form
