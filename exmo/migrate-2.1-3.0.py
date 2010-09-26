#!/usr/bin/python

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
