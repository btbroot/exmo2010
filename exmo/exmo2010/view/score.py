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

import datetime
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.utils import simplejson
from django.contrib.comments.signals import comment_was_posted
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
from exmo2010.forms import ClaimAddForm, ClarificationAddForm
from exmo2010.helpers import construct_change_message
from exmo2010.helpers import log_monitoring_interact_activity
from exmo2010.view.helpers import table_prepare_queryset
from exmo2010.models import Parameter, Score, Task, QAnswer, QQuestion
from exmo2010.models import Claim, Clarification, Monitoring
from exmo2010 import signals
from custom_comments.models import CommentExmo


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

    # Форма с презаполненными task и parameter, при вовзвращении реквеста
    # в исходниках Джанго, extra_context добавляется после создания
    # экземпляра класса формы, и перезаписывает переменную формы.
    form = ScoreForm(initial={'task': task,'parameter': parameter})

    return create_object(
        request,
        template_name='exmo2010/score/form.html',
        form_class = ScoreForm,
        model = Score,
        post_save_redirect = redirect,
        extra_context = {
            'task': task,
            'parameter': parameter,
            'title': parameter,
            'form': form,
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
    """
    Generic view для просмотра или изменения параметра, в зависимости от прав.
    """
    score = get_object_or_404(Score, pk=score_id)
    user = request.user
    all_score_claims = Claim.objects.filter(score=score)
    all_score_clarifications = Clarification.objects.filter(score=score)

    if user.has_perm('exmo2010.edit_score', score):
        redirect = "%s?%s#parameter_%s" % (
            reverse('exmo2010:score_list_by_task',
                args=[score.task.pk]),
            request.GET.urlencode(),
            score.parameter.code)
        redirect = redirect.replace("%","%%")
        title = _('Edit score %s') % score.parameter
        if request.method == 'POST':
            form = ScoreForm(request.POST, instance=score)
            message = construct_change_message(request, form, None)
            revision.comment = message
            if form.is_valid() and form.changed_data:
                signals.score_was_changed.send(
                    sender = Score.__class__,
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
            template_name = 'exmo2010/score/form.html',
            form_class = ScoreForm,
            object_id = score.pk,
            post_save_redirect = redirect,
            extra_context = {
                'task': score.task,
                'parameter': score.parameter,
                'title': title,
                'claim_list': all_score_claims,
                'clarification_list': all_score_clarifications,
                'claim_form' : ClaimAddForm(prefix="claim"),
                'clarification_form' : ClarificationAddForm(
                    prefix="clarification"),
                })
    elif user.has_perm('exmo2010.view_score', score):
        # Представители имеют права только на просмотр!
        title = _('Score for parameter "%s"') % score.parameter.name
        time_to_answer = score.task.organization.monitoring.time_to_answer
        delta = datetime.timedelta(days=time_to_answer)
        today = datetime.date.today()
        peremptory_day = today + delta
        return object_detail(
            request,
            template_name='exmo2010/score/detail.html',
            queryset = Score.objects.all(),
            object_id = score.pk,
            extra_context = {
                'title': title,
                'task': score.task,
                'parameter': score.parameter,
                'claim_list': all_score_claims,
                'clarification_list': all_score_clarifications,
                'peremptory_day' : peremptory_day,
                'view': True,
                'invcodeform': SettingsInvCodeForm(),
                'claim_form': ClaimAddForm(
                    prefix="claim"),
                'clarification_form': ClarificationAddForm(
                    prefix="clarification"),
                })
    else:
        return HttpResponseForbidden(_('Forbidden'))


def _save_comment(comment):
    comment.save()
    result = simplejson.dumps(
        {'success': True, 'status': comment.status})
    return HttpResponse(result, mimetype='application/json')


@login_required
def toggle_comment(request):
    if request.is_ajax() and request.method == 'POST':
        comment_id = request.POST['pk']
        comment = get_object_or_404(CommentExmo, pk=comment_id)

        if comment.status == CommentExmo.OPEN:
            comment.status = CommentExmo.NOT_ANSWERED
            return _save_comment(comment)
        elif comment.status in (CommentExmo.NOT_ANSWERED,
                                CommentExmo.ANSWERED):
            comment.status = CommentExmo.OPEN
            return _save_comment(comment)

    return Http404


def score_list_by_task(request, task_id, report=None):
    task = get_object_or_404(Task, pk=task_id)
    title = _('Score list for %s') % ( task.organization.name )
    if not request.user.has_perm('exmo2010.view_task', task):
        return HttpResponseForbidden(_('Forbidden'))
    monitoring = task.organization.monitoring
    parameters = Parameter.objects.filter(monitoring=monitoring).exclude\
        (exclude=task.organization)
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
                'report': report,
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
        # Не показываем ссылку экспертам B или предатвителям, если статус
        # мониторинга отличается от "Опубликован".
        user = request.user
        if (not user.is_active or
            (user.profile.is_expertB and not user.profile.is_expertA) or
            user.profile.is_organization) and \
           (monitoring.status != Monitoring.MONITORING_PUBLISH) and \
           not user.is_superuser:
            show_link = False
        else:
            show_link = True
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
                'show_link': show_link,
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
    score = get_object_or_404(Score, pk=score_id)
    if request.user.has_perm('exmo2010.add_comment_score', score):
        return render_to_response(
            'exmo2010/score_comment_form.html',
            {
                'score': score,
                'title': _('Add new comment'),
                },
            context_instance=RequestContext(request),
        )
    else: return HttpResponseForbidden(_('Forbidden'))


def log_user_activity(**kwargs):
    """
    Функция - обработчик сигнала при создании нового комментария.
    """
    comment = kwargs['comment']
    if comment.content_type.model == 'score':
        score = Score.objects.get(pk=comment.object_pk)
        log_monitoring_interact_activity(score.task.organization.monitoring,
            comment.user)


# Регистрируем обработчик сигнала.
comment_was_posted.connect(log_user_activity)


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
