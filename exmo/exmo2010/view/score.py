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

from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect, Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic.list_detail import object_detail
from django.views.generic.create_update import update_object, create_object
from django.views.generic.create_update import delete_object
from reversion import revision
from exmo2010.forms import ScoreForm, QuestionnaireDynForm, SettingsInvCodeForm
from exmo2010.helpers import construct_change_message
from exmo2010.helpers import log_monitoring_interact_activity
from exmo2010.view.helpers import table_prepare_queryset
from exmo2010.models import Parameter, Score, Task, QAnswer, QQuestion


@login_required
def score_add(request, task_id, parameter_id):
    task = get_object_or_404(Task, pk=task_id)
    parameter = get_object_or_404(Parameter, pk=parameter_id)
    try:
        score = Score.objects.get(parameter=parameter, task=task)
    except Score.DoesNotExist:
        pass
    else:
        return HttpResponseRedirect(reverse('exmo2010:score_view',
            args=(score.pk,)))
    if not request.user.has_perm('exmo2010.fill_task', task):
        return HttpResponseForbidden(_('Forbidden'))
    redirect = "%s?%s#parameter_%s" % (reverse('exmo2010:score_list_by_task',
        args=(task.pk,)), request.GET.urlencode(), parameter.code)
    redirect = redirect.replace("%","%%")
    return create_object(
        request,
        form_class = ScoreForm,
        post_save_redirect = redirect,
        extra_context = {
          'task': task,
          'parameter': parameter,
          'title': parameter,
        }
    )



@revision.create_on_success
@login_required
def score_manager(request, score_id, method='update'):
    score = get_object_or_404(Score, pk = score_id)
    redirect = "%s?%s#parameter_%s" % (reverse('exmo2010:score_list_by_task', args=[score.task.pk]), request.GET.urlencode(), score.parameter.code)
    redirect = redirect.replace("%","%%")
    if method == 'delete':
      title = _('Delete score %s') % score.parameter
      if request.user.has_perm('exmo2010.delete_score', score):
        return delete_object(request, model = Score, object_id = score.pk, post_delete_redirect = redirect, extra_context = {'title': title})
      else: return HttpResponseForbidden(_('Forbidden'))
    elif method == 'update':
        return score_view(request, score.pk)
    elif method == 'view':
        return score_view(request, score.pk)
    else: return HttpResponseForbidden(_('Forbidden'))



def score_view(request, score_id):
    score = get_object_or_404(Score, pk = score_id)
    redirect = "%s?%s#parameter_%s" % (reverse('exmo2010:score_list_by_task',
        args=[score.task.pk]), request.GET.urlencode(), score.parameter.code)
    redirect = redirect.replace("%","%%")
    if request.user.has_perm('exmo2010.edit_score', score):
        title = _('Edit score %s') % score.parameter
        if request.method == 'POST':
            form = ScoreForm(request.POST,instance=score)
            message = construct_change_message(request,form, None)
            revision.comment = message
            if form.is_valid() and form.changed_data:
                from exmo2010 import signals
                signals.score_was_changed.send(
                        sender  = Score.__class__,
                        form = form,
                        request = request,
                    )
            if score.active_claim:
                if form.is_valid() and form.changed_data:
                    score.close_claim(request.user)
                else:
                    return HttpResponse(_('Have active claim, but no data '
                                          'changed'))
        return update_object(
            request,
            form_class = ScoreForm,
            object_id = score.pk,
            post_save_redirect = redirect,
            extra_context = {
              'task': score.task,
              'parameter': score.parameter,
              'title': title,
            }
        )
    elif request.user.has_perm('exmo2010.view_score', score):
        #представители имеют права только на просмотр
        log_monitoring_interact_activity(score.task.organization.monitoring,
            request.user)
        title = _('View score %s') % score.parameter
        return object_detail(
            request,
            queryset = Score.objects.all(),
            object_id = score.pk,
            extra_context = {
              'task': score.task,
              'parameter': score.parameter,
              'title': title,
              'view': True,
            }
        )
    else:
        return HttpResponseForbidden(_('Forbidden'))


def score_list_by_task(request, task_id, report=None):
    task = get_object_or_404(Task, pk=task_id)
    title = _('Score list for %s') % ( task.organization.name )
    if not request.user.has_perm('exmo2010.view_task', task):
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = task.organization.monitoring
    parameters = Parameter.objects.filter(monitoring=monitoring).exclude\
        (exclude=task.organization)
    log_monitoring_interact_activity(monitoring, request.user)
    headers=(
        (_('Code'), None, None, None, None),
        (_('Parameter'), 'name', 'name', None, None),
        (_('Found'), None, None, None, None),
        (_('Complete'), None, None, None, None),
        (_('Topical'), None, None, None, None),
        (_('Accessible'), None, None, None, None),
        (_('HTML'), None, None, None, None),
        (_('Document'), None, None, None, None),
        (_('Image'), None, None, None, None),
        (_('Weight'), None, None, None, None),
    )
    parameters, extra_context = table_prepare_queryset(request, headers,
        queryset=parameters)

    scores_default = Score.objects.select_related().filter(
        parameter__in=parameters,
        revision=Score.REVISION_DEFAULT,
        task=task,
    )

    scores_interact = Score.objects.select_related().filter(
        parameter__in=parameters,
        revision=Score.REVISION_INTERACT,
        task=task,
    )

    score_dict = {}
    score_interact_dict = {}

    for score in scores_default:
        score_dict[score.parameter.pk] = score

    for score in scores_interact:
        score_interact_dict[score.parameter.pk] = score

    if report:
        # Print report
        extra_context.update(
            {
                'score_dict': score_dict,
                'parameters': parameters,
                'task': task,
                'title': title,
                'report': report
            }
        )
        return render_to_response(
            'exmo2010/task_report.html',
            extra_context,
            context_instance=RequestContext(request),
        )
    else:
        questionnaire = monitoring.get_questionnaire()
        if questionnaire and questionnaire.qquestion_set.exists():
            questions = questionnaire.qquestion_set.order_by("pk")
            if request.method == "POST":
                if not request.user.has_perm('exmo2010.fill_task', task):
                    return HttpResponseForbidden(_('Forbidden'))
                form = QuestionnaireDynForm(
                    request.POST,
                    questions=questions,
                    task=task,
                )
                if form.is_valid():
                    cd = form.cleaned_data
                    for answ in cd.items():
                        if answ[0].startswith("q_"):
                            try:
                                q_id = int(answ[0][2:])
                                question_obj = QQuestion.objects.get(pk=q_id)
                            except (ValueError, ObjectDoesNotExist):
                                continue
                            if answ[1]:  # Непустое значение ответа.
                                answer = QAnswer.objects.get_or_create(task=\
                                task, question=question_obj)[0]
                                if question_obj.qtype == 0:
                                    answer.text_answer = answ[1]
                                    answer.save()
                                elif question_obj.qtype == 1:
                                    answer.numeral_answer = answ[1]
                                    answer.save()
                                elif question_obj.qtype == 2:
                                    answer.variance_answer = answ[1]
                                    answer.save()
                            else:  # Пустой ответ.
                                try:
                                    answer = QAnswer.objects.get(task=task,
                                        question=question_obj)
                                except ObjectDoesNotExist:
                                    continue
                                else:
                                    answer.delete()
                    return HttpResponseRedirect(reverse(
                        'exmo2010:score_list_by_task', args=[task.pk]))
            else:
                existing_answers = task.get_questionnaire_answers()
                initial_data = {}
                for a in existing_answers:
                    initial_data["q_%s" % a.question.pk] = a.answer(True)
                form = QuestionnaireDynForm(questions=questions,
                    initial=initial_data)
        else:
            form = None
        has_npa = task.organization.monitoring.has_npa
        if has_npa:
            place_npa = task.rating_place_npa
            place_other = task.rating_place_other
            parameters_npa = parameters.filter(npa=True)
            parameters_other = parameters.filter(npa=False)
        else:
            place_npa = place_other = None
            parameters_npa = None
            parameters_other = parameters
        extra_context.update(
            {
                'score_dict': score_dict,
                'score_interact_dict': score_interact_dict,
                'parameters_npa': parameters_npa,
                'parameters_other': parameters_other,
                'task': task,
                'has_npa': has_npa,
                'title': title,
                'place': task.rating_place,
                'place_npa': place_npa,
                'place_other': place_other,
                'form': form,
                'invcodeform': SettingsInvCodeForm(),
            }
        )
        return render_to_response(
            'exmo2010/score_list.html',
            extra_context,
            context_instance=RequestContext(request),
        )


@csrf_protect
@login_required
def score_add_comment(request, score_id):
    score = get_object_or_404(Score, pk = score_id)
    if request.user.has_perm('exmo2010.comment_score', score):
        return render_to_response(
                'exmo2010/score_comment_form.html',
                {
                    'score': score,
                    'title': _('Add new comment'),
                },
                context_instance=RequestContext(request),
                )
    else: return HttpResponseForbidden(_('Forbidden'))


@login_required
def score_claim_color(request, score_id):
    """AJAX-вьюха для получения изображения для претензий"""
    score = get_object_or_404(Score, pk=score_id)
    if request.method == "GET" and request.is_ajax():
        return render_to_response('exmo2010/ajax/claim_image.html',
            {
                'score': score,
            },
            context_instance=RequestContext(request))
    else:
        raise Http404


@login_required
def score_comment_unreaded(request, score_id):
    """AJAX-вьюха для получения изображения для непрочитанных коментов"""
    score = get_object_or_404(Score, pk=score_id)
    if request.method == "GET" and request.is_ajax():
        return render_to_response('exmo2010/ajax/commentunread_image.html',
            {
                'score': score,
            },
            context_instance=RequestContext(request))
    else:
        raise Http404
