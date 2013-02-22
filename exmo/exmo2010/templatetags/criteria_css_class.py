# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012, 2013 Institute for Information Freedom Development
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

"""
Добавляет тег criteria_css_class который возвращет соотв. класс для CSS
в зависимости от оценки критерия и параметра оценки
"""

from django import template
register=template.Library()

@register.filter
def criteria_css_class(score, criteria):
        """Returns CSS class for criteria cell.
        Usage::
                {{ score|criteria_css_class:"complete" }}
        """
        weight = score.parameter.weight
        if weight >= 0:
            score_ok_nonzero = "score-ok-nonzero"
            score_ok_zero = "score-ok-zero"
        else:
            score_ok_nonzero = "score-ok-zero"
            score_ok_zero = "score-ok-nonzero"
        if criteria == 'found':
            if score.found: return score_ok_nonzero
            else: return score_ok_zero
        elif score.found:
            if score.parameter.__getattribute__(criteria):
                value = score.__getattribute__(criteria)
                if len(score._meta.get_field_by_name(criteria)[0].choices) > 2:
                    if value == 1:
                        return "score-ok-val1"
                    elif value == 2:
                        return "score-ok-val2"
                    elif value == 3:
                        return "score-ok-val3"
                    else:
                        return "score-none"
                else:
                    if value: return score_ok_nonzero
                    else: return score_ok_zero
            else:
                return "score-none"
        else:
            if score.parameter.__getattribute__(criteria):
                return score_ok_zero
            else:
                return "score-none"

criteria_css_class.is_safe = True
