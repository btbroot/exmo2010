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

from datetime import datetime
from django import template


register = template.Library()


@register.filter
def days_until(start_date, delta_days):
    """
    Считает количество оставшихся от настоящего времени дней до даты.
    Дата: (start_date) + количество дней (delta_days).
    Фильтр применяется к датам (date), в качестве аргумента принимает
    количество дней (int). Возвращает оставшиеся дни (int).
    Если просрочено, результат будет отрицательным числом.
    """

    if not isinstance(start_date, datetime):
        return None
    elif not isinstance(delta_days, (int, long)):
        return None
    else:
        time_delta = datetime.now() - start_date
        days = delta_days - time_delta.days
        return days


days_until.is_safe = False