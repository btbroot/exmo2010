# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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
from datetime import date, datetime

import bleach
from bleach import callbacks, linkify as bleach_linkify
from dateutil.rrule import rrule, DAILY, MO, TU, WE, TH, FR
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


bleach_args = {}

possible_settings = {
    'BLEACH_ALLOWED_ATTRIBUTES': 'attributes',
    'BLEACH_ALLOWED_STYLES': 'styles',
    'BLEACH_STRIP_TAGS': 'strip',
    'BLEACH_STRIP_COMMENTS': 'strip_comments',
}

for setting, kwarg in possible_settings.items():
    if hasattr(settings, setting):
        bleach_args[kwarg] = getattr(settings, setting)


@register.filter
def strict_bleach(value, allowed_tags=None):
    """
    Apply bleach.clean to input string, given list of allowed HTML tags.
    The allowed_tags argument should be a comma-separated string of HTML tags
    without angle-brackets, for example "a,br,div".
    """
    tags = [tag.strip() for tag in allowed_tags.split(',')] if allowed_tags else []

    return mark_safe(bleach.clean(value, tags=tags, **bleach_args))


@register.filter
def linkify(value, trim_url_limit=70):
    """
    Urlize strings that look like URLs or domain names in given html
    and truncate URLs in link text longer than limit.
    Add 'target="_blank"' and 'rel="nofollow"' attributes to all anchor tags
    found in the given text. Existing 'target' attributes will be overwritten.
    """
    return bleach_linkify(value, callbacks=[trim_links_callback(trim_url_limit),
                                            callbacks.target_blank, callbacks.nofollow])


def trim_links_callback(limit):
    """
    Trim text inside anchor tags.
    """
    def trim_links(attrs, new=False):
        if attrs['href'].startswith('mailto:'):
            return attrs

        text = attrs['_text']
        if len(text) > limit:
            attrs['_text'] = text[:limit-3] + '...'
        return attrs
    return trim_links


@register.filter
def date_until(start, limit):
    """
    Прибавляет к начальной дате количество рабочих дней.

    """
    return _next_date_generator(start, limit)


@register.filter
def workdays_still_left(start, limit):
    """
    Количество рабочих дней, оставшихся на сегодня до исчерпания периода.

    """
    next_date = _next_date_generator(start, limit)
    result = (next_date.date() - date.today()).days

    return result


def _next_date_generator(start, limit):
    """
    :param start: дата начала периода, datetime
    :param limit: величина периода в рабочих днях, int/long
    :return: возвращает новую дату, datetime

    """
    if not isinstance(start, datetime) or not isinstance(limit, (int, long)):
        return None
    workdays_generator = rrule(DAILY, byweekday=(MO, TU, WE, TH, FR), dtstart=start)
    next_date = workdays_generator[limit]

    return next_date
