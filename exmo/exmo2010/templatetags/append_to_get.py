# Copyright 2010 Al Nikolov <root@root.spb.ru>, Helsinki, Finland
# Copyright 2010 Institute of Information Freedom Development, non-profit partnership, Saint-Petersburg, Russia
#
# This file is part of EXMO2010 software.
#
# EXMO2010 is NOT distributable. NOBODY is permitted to use it without a written permission from the
# above copyright holders.
# http://djangosnippets.org/snippets/1627/
from django import template

register = template.Library()


"""
Decorator to facilitate template tag creation
"""
def easy_tag(func):
    """deal with the repetitive parts of parsing template tags"""
    def inner(parser, token):
        #print token
        try:
            return func(*token.split_contents())
        except TypeError:
            raise template.TemplateSyntaxError('Bad arguments for tag "%s"' % token.split_contents()[0])
    inner.__name__ = func.__name__
    inner.__doc__ = inner.__doc__
    return inner



class AppendGetNode(template.Node):
    def __init__(self, dict):
        self.dict_pairs = {}
        for pair in dict.split(','):
            pair = pair.split('=')
            self.dict_pairs[pair[0]] = template.Variable(pair[1])

    def render(self, context):
        get = context['request'].GET.copy()

        for key in self.dict_pairs:
            get[key] = self.dict_pairs[key].resolve(context)

        path = context['request'].META['PATH_INFO']

        #print "&".join(["%s=%s" % (key, value) for (key, value) in get.items() if value])

        if len(get):
            path += "?%s" % "&".join(["%s=%s" % (key, value) for (key, value) in get.items() if value])


        return path

@register.tag()
@easy_tag
def append_to_get(_tag_name, dict):
    return AppendGetNode(dict)