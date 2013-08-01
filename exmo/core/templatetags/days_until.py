# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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

import datetime
from dateutil import rrule
from dateutil.rrule import DAILY
from dateutil.rrule import MO, TU, WE, TH, FR
from django import template


register = template.Library()


@register.filter
def days_until(start_date, delta_days):
    """
    Возвращает количество оставшихся дней:
    от настоящего времени до даты (start_date + delta_days с учетом выходных).
    """
    if not isinstance(start_date, datetime.datetime):
        return None
    if not isinstance(delta_days, (int, long)):
        return None
    start_date.replace(second=0, microsecond=0)
    next_date = rrule.rrule(DAILY,
                            byweekday=(MO, TU, WE, TH, FR),
                            dtstart=start_date)
    next_date = next_date[delta_days].replace(second=0, microsecond=0)
    now = datetime.datetime.now().replace(second=0, microsecond=0)
    return (next_date - now).days


days_until.is_safe = False