# -*- coding: utf-8 -*-
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
#http://code.djangoproject.com/ticket/8399
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

import inspect
from django.contrib.comments.models import Comment
from django.contrib.auth.models import User



def disable_for_loaddata(signal_handler):
    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        for fr in inspect.stack():
            if inspect.getmodulename(fr[1]) in  ('loaddata','syncdb'):
                return
        signal_handler(*args, **kwargs)
    return wrapper



from dateutil import rrule
from dateutil.rrule import DAILY
def workday_count(alpha, omega):
    dates=rrule.rruleset() # create an rrule.rruleset instance
    dates.rrule(rrule.rrule(DAILY, dtstart=alpha, until=omega)) # this set is INCLUSIVE of alpha and omega
    dates.exrule(rrule.rrule(DAILY,
                        byweekday=(rrule.SA, rrule.SU),
                        dtstart=alpha))# here's where we exclude the weekend dates
    return len(list(dates)) # there's probably a faster way to handle this 




def safeConvert(string):
  if string and type(string) in [str, unicode]:
    return string.encode("utf-8")
  elif type(string) in [long, int]:
    return str(string)
  else:
    return ''

def ToType(string):
    #try convert to int, else -- string
    if not string: return None
    try:
        retval = int(string)
    except ValueError:
        retval = unicode(string, "utf-8")
    return string

#http://docs.python.org/library/csv#examples
import csv, codecs, cStringIO

class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
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
        return [ToType(s) for s in row]

    def __iter__(self):
        return self

    def _line_num(self):
        return self.reader.line_num

    line_num = property(_line_num)

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



def get_org_comments():
    return Comment.objects.filter(content_type__model='score',
        user__in=User.objects.filter(groups__name='organizations'))



def get_stat_answered_comments():
    """
    Возвращает {'answered': [], 'not_answered': []} за весь период, для всех мониторингов
    """
    org_comments = get_org_comments().order_by('-submit_date')

    operator_all_comments = Comment.objects.filter(
        content_type__model='score',
        user__in=User.objects.exclude(groups__name='organizations'),
    ).order_by('-submit_date')

    operator_all_comments_dict = {}

    for operator_comment in operator_all_comments:
        operator_all_comments_dict.setdefault(operator_comment.object_pk,[]).append(operator_comment)

    result = {'answered': [], 'not_answered': []}

    for org_comment in org_comments:
        if operator_all_comments_dict.has_key(org_comment.object_pk) and \
          operator_all_comments_dict[org_comment.object_pk][0].submit_date > org_comment.submit_date:
            result['answered'].append(org_comment.pk)
        else:
            result['not_answered'].append(org_comment.pk)
    return result
