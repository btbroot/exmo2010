from exmo.exmo2010.sort_headers import SortHeaders
from django.views.generic.list_detail import object_list

def table(request, headers, **kwargs):
  '''Generic sortable table view'''
  sort_headers = SortHeaders(request, headers)
  if sort_headers.get_order_by():
        kwargs['queryset'] = kwargs['queryset'].order_by(
        sort_headers.get_order_by())
  kwargs['queryset'] = kwargs['queryset'].filter(
    **sort_headers.get_filter()
  )
  if 'extra_context' not in kwargs:
    kwargs['extra_context'] = {}
  kwargs['extra_context'].update(
    {
      'headers': sort_headers.headers(),
    }
  )
  return object_list(request, **kwargs)
