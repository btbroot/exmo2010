#!/usr/bin/python
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

import simplejson

old_data = simplejson.load(open('data-2.1.json'))
new_data = []

for obj in old_data:
  # New model Monitoring
  if obj['model'] == 'exmo2010.organizationtype':
    new_data.append({
        'pk': obj['pk'],
        "model": "exmo2010.monitoring",
        "fields": { 'type': obj['pk'], "name": "-" }
      })
  # Fix model Task
  elif obj['model'] == 'exmo2010.task':
    obj['fields']['monitoring'] = [
      org['fields']['type']
        for org in old_data
          if org['model'] == 'exmo2010.organization' and
             org['pk']    == obj['fields']['organization']
    ][0]
    if obj['fields']['open']:
      obj['fields']['status'] = 0
    else:
      obj['fields']['status'] = 1
    del obj['fields']['open']
  # Fix model Parameter
  elif obj['model'] == 'exmo2010.parameter':
    obj['fields']['monitoring'] = obj['fields']['organizationType']
    del obj['fields']['organizationType']
  # Fix model Organization
  elif obj['model'] == 'exmo2010.organization':
    obj['fields']['keyname'] = str(obj['pk'])
  new_data.append(obj)

simplejson.dump(new_data, open('data-3.0.json', 'w'))
