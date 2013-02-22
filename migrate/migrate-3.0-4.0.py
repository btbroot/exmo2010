#!/usr/bin/python
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012, 2013 Institute for Information Freedom Development
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

import simplejson

old_data = simplejson.load(open('data-3.0.json'))
new_data = []

for obj in old_data:
  # New model ParameterMonitoringProperties
  if obj['model'] == 'exmo2010.parameter':
    new_data.append({
        'pk': obj['pk'],
        "model": "exmo2010.parametermonitoringproperty",
        "fields": { 'monitoring': obj['fields']['monitoring'][0], 'parameter': obj['pk'], 'weight': obj['fields']['weight']}
      })
    del obj['fields']['weight']
    del obj['fields']['monitoring']
  # New model ApprovedTask
  if obj['model'] == 'exmo2010.task':
    if obj['fields']['status'] == 2:
      new_data.append({
          'pk': obj['pk'],
          "model": "exmo2010.approvedtask",
          "fields": { 'task': obj['pk'], 'organization': obj['fields']['organization'], 'monitoring': obj['fields']['monitoring'] }
        })
      obj['fields']['closed'] = True
    else:
      obj['fields']['closed'] = obj['fields']['status'] == 1
    del obj['fields']['status']
  new_data.append(obj)

simplejson.dump(new_data, open('data-4.0.json', 'w'))
