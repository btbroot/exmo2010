#!/usr/bin/python

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
