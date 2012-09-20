# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
from django.views.generic.list_detail import object_list
from exmo2010.sort_headers import SortHeaders
from exmo2010.models import Task


def table_prepare_queryset(request, headers, queryset):
  """Generic sortable table view"""
  sort_headers = SortHeaders(request, headers)
  if sort_headers.get_order_by():
        queryset = queryset.order_by(sort_headers.get_order_by())
  queryset = queryset.filter(**sort_headers.get_filter())
  extra_context = {'headers': sort_headers.headers(),}
  return queryset, extra_context


def table(request, headers, **kwargs):
  kwargs['queryset'], extra_context = table_prepare_queryset(request, headers, kwargs['queryset'])
  if 'extra_context' not in kwargs:
    kwargs['extra_context'] = extra_context
  else:
    kwargs['extra_context'].update(extra_context)
  return object_list(request, **kwargs)


def rating(monitoring, parameters=None):
    #sample extra for select
    extra_select = "count(*)"
    #get task from monitoring for valid sql
    generic_task_qs=Task.objects.filter(organization__monitoring=monitoring)
    if generic_task_qs.exists():
        extra_select = generic_task_qs[0]._sql_openness(parameters)

    object_list = [
        {
            'task': task,
            'openness': task.__task_openness or 0,
            'openness_first': task.openness_first,
        } for task in Task.approved_tasks.filter(
        organization__monitoring=monitoring
        ).extra(select={
            '__task_openness': extra_select,
        }).order_by('-__task_openness')
    ]

    place = 1
    avg = {
        'openness': 0,
        'openness_first': 0,
    }
    max_rating = 0
    if object_list:
        max_rating = object_list[0]['openness']
        avg['openness'] = sum([t['openness'] for t in object_list])/len(object_list)
        avg['openness_first'] = sum([t['openness_first'] for t in object_list])/len(object_list)
    rating_list = []
    place_count={}
    for rating_object in object_list:
        if rating_object['openness'] < max_rating:
            place+=1
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
