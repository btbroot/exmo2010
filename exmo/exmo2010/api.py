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
Не актуально
"""

from django.utils import simplejson
from django.http import HttpResponse
from exmo2010.models import Organization
from django.db.models import Q


def organization_lookup(request):
    # Default return list
    results = []
    if request.method == "GET":
        if u'q' in request.GET:
            value = request.GET[u'q']
            # Ignore queries shorter than length 3
            if len(value) > 2:
                for word in value.split(" "):
                    model_results = Organization.objects.filter(
                                                            Q(name__icontains=word) |
                                                            Q(keywords__icontains=word) |
                                                            Q(url__icontains=word)
                                                         )
                results = [ x.name for x in model_results ]
    json = ""
    for x in results:
        json = "%s \n %s" % (x, json)
#    json = simplejson.dumps(results)
    return HttpResponse(json, mimetype='application/json')
