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
import urllib, string

# http://djangosnippets.org/snippets/308/

ORDER_VAR = 'o'
ORDER_TYPE_VAR = 'ot'
FILTER_PREFIX = 'filter'

class SortHeaders:
    """
    Handles generation of an argument for the Django ORM's
    ``order_by`` method and generation of table headers which reflect
    the currently selected sort, based on defined table headers with
    matching sort criteria.

    Based in part on the Django Admin application's ``ChangeList``
    functionality.
    """
    def __init__(self, request, headers, default_order_field=None,
            default_order_type='asc', additional_params=None):
        """
        request
            The request currently being processed - the current sort
            order field and type are determined based on GET
            parameters.

        headers
            A list of two-tuples of header text and matching ordering
            criteria for use with the Django ORM's ``order_by``
            method. A criterion of ``None`` indicates that a header
            is not sortable.

        default_order_field
            The index of the header definition to be used for default
            ordering and when an invalid or non-sortable header is
            specified in GET parameters. If not specified, the index
            of the first sortable header will be used.

        default_order_type
            The default type of ordering used - must be one of
            ``'asc`` or ``'desc'``.

        additional_params:
            Query parameters which should always appear in sort links,
            specified as a dictionary mapping parameter names to
            values. For example, this might contain the current page
            number if you're sorting a paginated list of items.
        """
#        if default_order_field is None:
#            for i, (header, order_criterion, filter_criterion, filter_func) in enumerate(headers):
#                if order_criterion is not None:
#                    default_order_field = i
#                    break
#        if default_order_field is None:
#            raise AttributeError('No default_order_field was specified and none of the header definitions given were sortable.')
        if default_order_type not in ('asc', 'desc'):
            raise AttributeError('If given, default_order_type must be one of \'asc\' or \'desc\'.')
        if additional_params is None: additional_params = {}

        self.header_defs = headers
        self.additional_params = additional_params
#        self.order_field, self.order_type = default_order_field, default_order_type
        self.order_field, self.order_type = None, default_order_type
        self.filter_field, self.filter_pattern = [],[]

        # Determine order field and order type for the current request
        params = dict(request.GET.items())
        self.params = params # Save them for further update
        if ORDER_VAR in params:
            try:
                new_order_field = int(params[ORDER_VAR])
                if headers[new_order_field][1] is not None:
                    self.order_field = new_order_field
            except (IndexError, ValueError):
                pass # Use the default
        if ORDER_TYPE_VAR in params and params[ORDER_TYPE_VAR] in ('asc', 'desc'):
            self.order_type = params[ORDER_TYPE_VAR]
        for k,v in params.items():
          if k.startswith(FILTER_PREFIX):
            try:
                new_filter_field = int(string.replace(k, FILTER_PREFIX, ''))
                if headers[new_filter_field][1] is not None:
                    self.filter_field.append(new_filter_field)
                    self.filter_pattern.append(urllib.unquote(v))
            except (IndexError, ValueError):
                pass # Use the default

    def headers(self):
        """
        Generates dicts containing header and sort link details for
        all defined headers.
        """
        for i, (header, order_criterion, filter_criterion, filter_func, choices) in enumerate(self.header_defs):
            th_classes = []
            new_order_type = 'asc'
            if i == self.order_field:
                th_classes.append('sorted %sending' % self.order_type)
                new_order_type = {'asc': 'desc', 'desc': 'asc'}[self.order_type]
            if i == self.filter_field:
              pattern = self.filter_pattern
            else:
              pattern = ''
            yield {
                'text': header,
                'sortable': order_criterion is not None,
                'filterable': filter_criterion is not None,
                'filter': pattern,
                'select': choices,
                'i': i,
                'o': self.order_field,
                'ot': self.order_type,
                'url': self.get_query_string({ORDER_VAR: i, ORDER_TYPE_VAR: new_order_type}),
                'class_attr': (th_classes and ' class="%s"' % ' '.join(th_classes) or ''),
            }

    def get_query_string(self, params):
        """
        Creates a query string from the given dictionary of
        parameters, including any additonal parameters which should
        always be present.
        """
        finalparams = self.params # Remember what params were in the beginning
        finalparams.update(params) # Now override them
        params = finalparams # Now as before
        params.update(self.additional_params)
        return '%s' % '&'.join(['%s=%s' % (param, value) \
                                     for param, value in params.items()])

    def get_order_by(self):
        """
        Creates an ordering criterion based on the current order
        field and order type, for use with the Django ORM's
        ``order_by`` method.
        """
        if self.order_type and self.order_field:
            return '%s%s' % (
                self.order_type == 'desc' and '-' or '',
                self.header_defs[self.order_field][1],
            )

    def get_filter(self):
     filter_dict = {}
     for el in self.filter_field:
      c = self.filter_field.index(el)
      if (self.filter_field[c] != None) and self.filter_pattern[c]:
        func = self.header_defs[self.filter_field[c]][3]
        if func:
          pattern = func(self.filter_pattern[c])
        else:
          pattern = self.filter_pattern[c]
        filter_dict[self.header_defs[self.filter_field[c]][2] + '__icontains'] = pattern
     return filter_dict
