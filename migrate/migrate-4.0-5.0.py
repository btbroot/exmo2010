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

old_data = simplejson.load(open('data-4.0.json'))
new_data = []

for obj in old_data:
  # Delete model ApprovedTask
  if obj['model'] == 'exmo2010.approvedtask':
    continue
  # Fix model Task
  elif obj['model'] == 'exmo2010.task':
    if [ o for o in old_data
           if o['model'] == 'exmo2010.approvedtask'
           and o['fields']['task'] == obj['pk'] ]:
      obj['fields']['status'] = 2
    elif obj['fields']['closed']:
      obj['fields']['status'] = 1
    else:
      obj['fields']['status'] = 0
    del obj['fields']['closed']
  new_data.append(obj)

simplejson.dump(new_data, open('data-5.0.json', 'w'))
