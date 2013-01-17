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

import datetime
from django import template


register = template.Library()


@register.filter
def date_until(start_date, delta_days):
    """
    Прибавляет к дате количество дней
    и возвращает новую дату.
    """
    if not isinstance(start_date, datetime.datetime):
        return None
    if not isinstance(delta_days, (int, long)):
        return None

    delta = datetime.timedelta(days=delta_days)
    final_date = start_date + delta
    return final_date


date_until.is_safe = False