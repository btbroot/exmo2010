# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2015 IRSI LTD
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
import codecs
import cStringIO
import csv
from datetime import timedelta, datetime
from decimal import Decimal
import re

from django.conf import settings
from django.core.urlresolvers import get_resolver, RegexURLResolver
from django.utils.safestring import mark_safe
from lxml.html.clean import Cleaner


# datetime.weekday() values start from 0.
LAST_WORKDAY = 4


def workday_count(start, end):
    """
    Count days diff excluding weekends
    """
    if isinstance(start, datetime):
        start = start.date()
    if isinstance(end, datetime):
        end = end.date()

    if start.weekday() > LAST_WORKDAY:
        # If start day is weekend, move start forward to nearest workday
        start += timedelta(7 - start.weekday())

    if end.weekday() > LAST_WORKDAY:
        # If end day is weekend, move end back to nearest workday
        end -= timedelta(end.weekday() - LAST_WORKDAY)

    if end <= start:
        return 0

    # (In examples below, week begins on Monday, as in most Europe countries)
    # From Friday to Monday (day 08 to 11)
    #  daydiff == -4
    #  nweeks == 1
    #  result == 5 - 4
    # From Monday to Tuesday (day 04 to 12)
    #  daydiff == 1
    #  nweeks == 1
    #  result == 5 + 1
    daydiff = end.weekday() - start.weekday()
    nweeks = ((end - start).days - daydiff) / 7

    return nweeks * 5 + daydiff


def safeConvert(string):
    """
    Безопасное приведение к utf-8.

    """
    if string and type(string) in [str, unicode]:
        return string.encode("utf-8")
    elif type(string) in [long, int]:
        return str(string)
    else:
        return ''


#http://docs.python.org/library/csv#examples
class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8.

    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.

    """
    def __init__(self, f, dialect=csv.excel, encoding="UTF-16", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


class UnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.

    """
    def __init__(self, f, dialect=csv.excel, encoding="UTF-16", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([safeConvert(s) for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def clean_message(comment):
    if len(comment) == 0:
        return mark_safe(comment)

    # prevent XSS-attacks, remove not allowed tags
    allowed_tags = 'a blockquote br div em li ol p span strong u ul'.split()
    comment = Cleaner(remove_unknown_tags=False, allow_tags=allowed_tags).clean_html(comment)
    # remove redundant lines
    comment = re.sub(r'(<br>(?=(<br>){2,}))', '', comment)
    comment = re.sub(r'(?<=^(<span>))(<br>){1,2}|(<br>){1,4}(?=(</span>)$)', '', comment)
    comment = re.sub(r'(<br>){1,2}(?=(</p>)$)', '', comment)
    return mark_safe(comment)


def get_named_patterns():
    resolver = get_resolver(settings.ROOT_URLCONF)
    return list(iter_named_patterns(resolver))


def iter_named_patterns(root_resolver):
    '''
    Recursively iterate over all named urlpatterns in the resolver
    Will also set pattern _full_name as "app_name:name"
    '''
    if not hasattr(root_resolver, '_app_name'):
        root_resolver._app_name = root_resolver.app_name

    for child in root_resolver.url_patterns:
        child._app_name = getattr(child, 'app_name', None) or root_resolver._app_name
        name = getattr(child, 'name', None)
        if isinstance(child, RegexURLResolver):
            # This is RegexURLResolver, we should iterate deeper into it
            for p in iter_named_patterns(child):
                yield p
        elif name:
            # This is RegexURLPattern with proper name. We will construct full name
            if child._app_name:
                child._full_name = '%s:%s' % (child._app_name, name)
            else:
                child._full_name = name
            yield child


def round_ex(x):
    """
    If x < 0.1, round to the first nonzero decimal digit, Otherwise round to one decimal digit.
    0.0 => 0.0
    0.00123 => 0.001
    0.54321 => 0.5
    """
    if x == 0.0:
        return x
    elif x < 0.1:
        _x = Decimal(x).as_tuple()
        return round(x, 1 - _x.exponent - len(_x.digits))
    else:
        return round(x, 1)


def dictfetchall(cursor):
    """
    Returns all rows from a cursor as a list of dictionaries.
    """
    keys = [col[0] for col in cursor.description]
    return [dict(zip(keys, values)) for values in cursor.fetchall()]
