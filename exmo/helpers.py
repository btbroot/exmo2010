# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011 Institute for Information Freedom Development
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

