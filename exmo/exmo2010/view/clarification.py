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

"""
Модуль для работы с уточнениями
"""

from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from exmo2010.models import Score, Clarification
from exmo2010.forms import ClarificationAddForm


@login_required
def clarification_create(request, score_id):
    """
    Добавление уточнения на странице параметра
    """
    user = request.user
    score = get_object_or_404(Score, pk=score_id)
    redirect = reverse('exmo2010:score_view', args=[score.pk])
    redirect += '#clarifications' # Named Anchor для открытия нужной вкладки
    if request.method == 'POST' and (
        user.has_perm('exmo2010.add_clarification_score', score) or
        user.has_perm('exmo2010.answer_clarification_score', score)):
        form = ClarificationAddForm(request.POST, prefix="clarification")
        if form.is_valid():
            # Если заполнено поле clarification_id,
            # значит это ответ на уточнение
            if (form.cleaned_data['clarification_id'] is not None and
                user.has_perm('exmo2010.answer_clarification_score', score)):
                clarification_id = form.cleaned_data['clarification_id']
                clarification = get_object_or_404(Clarification,
                                                  pk=clarification_id)
                answer = form.cleaned_data['comment']
                clarification.add_answer(user, answer)
            else:
                # Если поле claim_id пустое, значит это выставление уточнения
                clarification = score.add_clarification(
                    user, form.cleaned_data['comment'])

            return HttpResponseRedirect(redirect)

        else:
            return render_to_response(
                'exmo2010/score/clarification_form.html',
                {
                    'monitoring': score.task.organization.monitoring,
                    'task': score.task,
                    'score': score,
                    'title': _('Add new claim for %s') % score,
                    'form': form,
                },
                context_instance=RequestContext(request),
            )
    else:
        raise Http404