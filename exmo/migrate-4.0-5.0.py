#!/usr/bin/python

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
