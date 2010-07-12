# Copyright 2010 Al Nikolov <root@toor.spb.ru>, Helsinki, Finland
# Copyright 2010 Institute of Information Freedom Development, non-profit partnership, Saint-Petersburg, Russia
#
# This file is part of EXMO2010 software.
#
# EXMO2010 is NOT distributable. NOBODY is permitted to use it without a written permission from the
# above copyright holders.
from django import template

def table_header(context, headers):
    return {
        'headers': headers,
    }

register = template.Library()
register.inclusion_tag('exmo2010/table_header.html', takes_context=True)(table_header)