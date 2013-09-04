# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012, 2013 Foundation "Institute for Information Freedom Development"
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

from dateutil.rrule import rrule, DAILY, MO, TU, WE, TH, FR
from django import template


register = template.Library()


@register.filter(is_safe=False)
def workdays_still_left(start, limit):
    """
    Количество рабочих дней, оставшихся на сегодня до исчерпания периода.
    start: дата начала периода, datetime
    limit: величина периода в рабднях, int/long

    """
    if not isinstance(start, datetime):
        return None
    if not isinstance(limit, (int, long)):
        return None
    workdays_generator = rrule(DAILY, byweekday=(MO, TU, WE, TH, FR), dtstart=start)
    next_date = workdays_generator[limit]
    today = date.today()
    result = (next_date.date() - today).days

    return result
