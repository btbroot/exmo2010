# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Foundation "Institute for Information Freedom Development"
# Copyright 2013 Al Nikolov
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

from collections import namedtuple
from copy import copy

from django.core.urlresolvers import reverse, resolve

from core.utils import get_named_patterns


# Crumb is an intermediate node type. `parents` are list of ancestors urlnames.
# Crumbs are internally organized in a dict by urlnames.
Crumb = namedtuple('Crumb', 'urlname title pattern parents')


def traverse_tree(tree, ancestor_keys=[]):
    '''
    Recursively iterates into `tree` and yields (key, title, ancestor_keys)
    '''
    for key in tree:
        try:
            title, subtree = tree[key]
        except ValueError:
            # leaf node without children
            title, subtree = tree[key], None
        if subtree:
            for x in traverse_tree(subtree, ancestor_keys + [key]):
                yield x
        yield (key, title, ancestor_keys)


def crumbs_dict(crumbs_tree):
    '''
    Constructs flat crumbs_dict from `crumbs_tree`
    crumbs_dict is a dict of Crumb nodes by urlnames
    `crumbs_tree` should have following structure:
    {
        urlname: (title, {
            urlname: title,  # leaf node without children
            urlname: (title, { ... }),  # node with more children
            ... ,
        }),
        ... ,
    }
    '''
    crumbs_dict = {}
    patterns = dict((p.name, p) for p in get_named_patterns())
    for urlname, title, parents in traverse_tree(crumbs_tree):
        pat = patterns[urlname]
        if len(pat.regex.groupindex) == 0:
            # pattern does not have arguments and can be reversed right now as optimization
            pat = reverse(pat._full_name)
        crumbs_dict[urlname] = Crumb(urlname, title, pat, parents)
    return crumbs_dict


def walk_crumb_path(urlname, crumbs_dict):
    crumb = crumbs_dict.get(urlname)
    if crumb is None:
        return
    for parent_urlname in crumb.parents:
        yield crumbs_dict[parent_urlname]
    yield crumb


class BreadcrumbsMiddleware(object):
    '''
    This middleware constructs breadcrumbs and adds them to the response context.
    '''
    def process_template_response(self, request, response):
        '''
        Constructs breadcrumbs -- list of dicts {url, urlname, title}
        Adds two items to response.context_data:
          'breadcrumbs': constructed breadcrumbs
          'breadcrumb_last': last item in the breadcrumbs
        '''
        if response.is_rendered:
            # response was rendered (fetched from cache), do nothing
            return response

        if response.context_data is None:
            response.context_data = {}

        if 'breadcrumbs' in response.context_data:
            # Someone already constructed breadcrumbs manually
            return response

        crumbs_dict = self.get_crumbs_dict(request)

        # TODO: Upgrade to django 1.5, use HttpRequest.resolver_match instead of resolving here
        urlmatch = resolve(request.path_info)

        crumb_path = list(walk_crumb_path(urlmatch.url_name, crumbs_dict))
        if not crumb_path:
            # this page was not found in the crumbs_dict, no breadcrumbs
            return response

        kwargs = self.infer_kwargs(urlmatch.kwargs)
        breadcrumbs = self.get_breadcrumbs(crumb_path, kwargs)
        response.context_data.update(
            breadcrumbs = breadcrumbs,
            breadcrumb_last = breadcrumbs[-1]
        )
        return response

    def get_breadcrumbs(self, crumb_path, kwargs):
        '''
        Builds breadcrumbs from path of Crumb nodes, reversing their urlpatterns

        :param crumb_path: list of Crumb nodes from root to current page
        :param kwargs: dict of all needed kwargs to reverse patterns

        :returns: breadcrumbs -- list of dicts {url, urlname, title}
        '''
        breadcrumbs = []
        for crumb in crumb_path:
            pat = crumb.pattern
            if isinstance(pat, (str, unicode)):
                # pattern is static and was already reversed into url
                url = pat
            else:
                # fetch needed kwargs for reverse
                url_kwargs = dict((k, kwargs[k]) for k in pat.regex.groupindex if kwargs.get(k))
                url = reverse(pat._full_name, kwargs=url_kwargs)

            breadcrumbs.append({'url': url, 'urlname': crumb.urlname, 'title': crumb.title})

        return breadcrumbs

    def infer_kwargs(self, initial_kwargs):
        '''
        Infer all needed kwargs for parent crumbs patterns.
        This method can be overloaded in custom middleware for project

        :param initial_kwargs: kwargs for currently requested url

        :returns: dict -- all inferred kwargs
        '''
        return copy(initial_kwargs)
