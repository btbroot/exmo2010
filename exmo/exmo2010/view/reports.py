# -*- coding: utf-8 -*-
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
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.db.models import Count
from django.contrib.auth.models import User
from exmo2010.models import UserProfile, SEX_CHOICES

SEX_CHOICES_DICT = dict(SEX_CHOICES)

def gender_stats(request):
    """
    Страница гендерной статистики.
    """
    external_users = User.objects.exclude(is_superuser=True).exclude(is_staff=True).exclude(groups__name__in=UserProfile.expert_groups)
    result = external_users.values_list('userprofile__sex').order_by('userprofile__sex').annotate(Count('userprofile__sex'))
    result_list = []
    for val, count in result:
        if val is not None:  # Workaround для косяка MySQL в django.
            result_list.append((SEX_CHOICES_DICT[val], count))
    result_list.append((_("Total"), external_users.count()))
    return render_to_response('exmo2010/gender_stats.html',
            {"results": result_list,}, RequestContext(request))
