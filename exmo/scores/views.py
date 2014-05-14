# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
import json

from ckeditor.fields import RichTextFormField
from ckeditor.widgets import CKEditorWidget
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Max
from django.forms import RadioSelect
from django.forms.models import modelform_factory
from django.http import HttpResponseForbidden, HttpResponseRedirect, Http404, HttpResponseNotAllowed, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from livesettings import config_value

from accounts.forms import SettingsInvCodeForm
from core.helpers import table_prepare_queryset
from core.response import JSONResponse
from core.utils import clean_message, urlize
from custom_comments.models import CommentExmo
from exmo2010.mail import mail_comment
from exmo2010.models import Score, Task, Parameter, QQuestion, QAnswer, UserProfile
from exmo2010.models.monitoring import Monitoring
from perm_utils import annotate_exmo_perms
from questionnaire.forms import QuestionnaireDynForm


# The cache_control decorator will force the browser to make request to server, when user clicks 'back'
# button after add new Score. BUT, not working in Opera browser:
# (http://my.opera.com/yngve/blog/2007/02/27/introducing-cache-contexts-or-why-the).
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def score_view(request, **kwargs):
    if request.method not in ['POST', 'GET']:
        return HttpResponseNotAllowed(['POST', 'GET'])

    if 'score_pk' in kwargs:
        # Score edit or view
        score = get_object_or_404(Score, pk=kwargs['score_pk'])
        task = score.task
        param = score.parameter
        if request.method == 'POST' and not request.user.has_perm('exmo2010.edit_score', score):
            raise PermissionDenied
        if request.method == 'GET' and not request.user.has_perm('exmo2010.view_score', score):
            raise PermissionDenied
    else:
        # Score creation by task and param
        task = get_object_or_404(Task, pk=kwargs['task_pk'])
        param = get_object_or_404(Parameter, pk=kwargs['parameter_pk'])
        if not request.user.has_perm('exmo2010.fill_task', task):
            raise PermissionDenied

        # Check if score already exist.
        try:
            score = Score.objects.get(parameter=param, task=task, revision=Score.REVISION_DEFAULT)
        except Score.DoesNotExist:
            # OK, score does not exist and can be created.
            score = Score(parameter=param, task=task, revision=Score.REVISION_DEFAULT)
        else:
            # User requested score creation by task and param, but score already exist.
            if request.user.has_perm('exmo2010.view_score', score):
                # Redirect user to GET score page, even if current request method is POST.
                # This way duplicate POST to create score will be ignored.
                return HttpResponseRedirect(reverse('exmo2010:score_view', args=[score.pk]))
            else:
                raise PermissionDenied

    org = task.organization

    # Relevant criteria names
    criteria = ['found'] + filter(param.__getattribute__, Parameter.OPTIONAL_CRITERIONS)

    ScoreForm = modelform_factory(
        Score,
        fields=criteria + ['recommendations', 'links', 'editor'],
        widgets=dict((crit, RadioSelect) for crit in criteria))

    ScoreForm.base_fields['comment'] = RichTextFormField(config_name='advanced', required=False)

    # Replace '-----' with '-' in empty radio choices.
    for f in criteria:
        ScoreForm.base_fields[f].widget.choices[0] = ('', '–')

    form = ScoreForm(request.POST if request.method == 'POST' else None, instance=score)

    if request.method == 'POST' and form.is_valid():
        if score.pk and not request.user.has_perm('exmo2010.edit_score', score):
            raise PermissionDenied

        with transaction.commit_on_success():
            if org.monitoring.status in Monitoring.after_interaction_status and 'score_pk' in kwargs:
                if not Score.objects.filter(parameter=param, task=task, revision=Score.REVISION_INTERACT).exists():
                    # Initial revision does not exist and should be created. It will have new pk.
                    initial_score = Score.objects.get(pk=kwargs['score_pk'])
                    initial_score.pk = None
                    initial_score.revision = Score.REVISION_INTERACT
                    initial_score.save()

                if 'comment' in request.POST:
                    _add_comment(request, score)
            score = form.save(commit=False)
            score.editor = request.user
            score.save()
        if org.monitoring.is_interact or org.monitoring.is_finishing:
            return HttpResponseRedirect(reverse('exmo2010:score_view', args=[score.pk]))
        else:
            url = reverse('exmo2010:task_scores', args=[task.pk])
            return HttpResponseRedirect('%s#parameter_%s' % (url, param.code))

    score_rev1 = Score.objects.filter(parameter=param, task=task, revision=Score.REVISION_INTERACT)
    score_table = [{
        'label': score._meta.get_field_by_name(criterion)[0].verbose_name,
        'score': getattr(score, criterion),
        'score_rev1': getattr(score_rev1[0], criterion) or '-' if score_rev1 else '',
        'criterion': criterion,
        'max_score': getattr(score, criterion) == score._meta.get_field(criterion).choices[-1][-1]
    } for criterion in criteria]

    score_delta = score.openness - score_rev1[0].openness if score_rev1 else 0
    if request.user.is_expert:
        show_rev1 = True
    elif request.user.is_anonymous():
        show_rev1 = False
    else:
        show_rev1 = request.user.profile.show_score_rev1

    all_max = True  # Flag if all criteria set to max
    for crit in criteria:
        if getattr(score, crit) != score._meta.get_field(crit).choices[-1][-1]:
            all_max = False

    criteria = [form[crit] for crit in criteria]
    for boundfield in criteria:
        # Add attribute with initial value to each criterion boundfield
        boundfield.initial = form.initial.get(boundfield.name, boundfield.field.initial)

    if request.user.is_expertA:
        claim_list = score.claim_set.all()
    elif request.user.is_expertB:
        claim_list = score.claim_set.filter(addressee=request.user)
    else:
        claim_list = []

    CommentForm = modelform_factory(CommentExmo, widgets={'comment': CKEditorWidget(config_name='simplified')})
    context = {
        'form': form,
        'score': annotate_exmo_perms(score, request.user),
        'score_rev1': annotate_exmo_perms(score_rev1[0] if score_rev1 else None, request.user),
        'param': annotate_exmo_perms(param, request.user),
        'org': org,
        'score_table': score_table,
        'score_delta': score_delta,
        'show_rev1': show_rev1,
        'masked_expert_name': _(config_value('GlobalParameters', 'EXPERT')),
        'criteria': criteria,
        'interaction': org.monitoring.is_interact or org.monitoring.is_finishing,
        'url_length': 70,
        'claim_list': claim_list,
        'all_max_initial': all_max,
        'comment_form': CommentForm(request.POST if request.method == 'POST' else None),
        'invcodeform': SettingsInvCodeForm(),
    }

    return TemplateResponse(request, 'scores/score.html', context)


def post_score_comment(request, score_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    score = get_object_or_404(Score, pk=score_pk)
    if not request.user.has_perm('exmo2010.add_comment', score):
        raise PermissionDenied

    _add_comment(request, score)
    return HttpResponseRedirect(reverse('exmo2010:score_view', args=[score.pk]))


def _add_comment(request, score):
    comment = CommentExmo.objects.create(
        object_pk=score.pk,
        content_type=ContentType.objects.get_for_model(Score),
        user=request.user,
        comment=clean_message(request.POST['comment']),
        site_id=1)

    if request.user.is_expert:
        # Expert comment. Close existing org represenatives comments for this score.
        org_comments = CommentExmo.objects.filter(
            object_pk=score.pk,
            status=CommentExmo.OPEN,
            user__userprofile__organization__isnull=False)

        org_comments.update(status=CommentExmo.ANSWERED, answered_date=datetime.now())
    else:
        # Org represenative comment, update org status to "Active"
        org = score.task.organization
        if org.inv_status == 'RGS' and org in request.user.profile.organization.all():
            org.inv_status = 'ACT'
            org.save()

    mail_comment(request, comment)


def post_recommendations(request, score_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    score = get_object_or_404(Score, pk=score_pk)
    if not request.user.has_perm('exmo2010.edit_score', score):
        raise PermissionDenied

    score.recommendations = request.POST['recommendations']
    try:
        score.full_clean()
    except ValidationError:
        return HttpResponseBadRequest()
    score.save()
    return JSONResponse({'data': urlize(score.recommendations.replace('\n', '<br />'))})


def post_score_links(request, score_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    score = get_object_or_404(Score, pk=score_pk)
    if not request.user.has_perm('exmo2010.edit_score', score):
        raise PermissionDenied

    score.links = request.POST['links']
    score.save()
    return JSONResponse({'data': urlize(score.links.replace('\n', '<br />'))})


@login_required
def toggle_comment(request):
    if request.is_ajax() and request.method == 'POST':
        comment = get_object_or_404(CommentExmo, pk=request.POST['pk'])

        if comment.status == CommentExmo.OPEN:
            comment.status = CommentExmo.NOT_ANSWERED
            comment.save()
            return JSONResponse(success=True, status=comment.status)
        elif comment.status in (CommentExmo.NOT_ANSWERED, CommentExmo.ANSWERED):
            comment.status = CommentExmo.OPEN
            comment.save()
            return JSONResponse(success=True, status=comment.status)

    raise Http404


def task_scores_print(request, task_pk):
    task = get_object_or_404(Task, pk=task_pk)

    if not request.user.has_perm('exmo2010.view_task', task):
        raise PermissionDenied

    task_scores_url = reverse('exmo2010:task_scores', args=(task.pk, ))
    return TemplateResponse(request, 'scores/task_scores_print.html', {
        'task': task,
        'task_scores_url': request.build_absolute_uri(task_scores_url)})


def task_scores(request, task_pk):
    task = get_object_or_404(Task, pk=task_pk)
    title = task.organization.name

    if not request.user.has_perm('exmo2010.view_task', task):
        raise PermissionDenied

    monitoring = task.organization.monitoring
    parameters = Parameter.objects.filter(monitoring=monitoring).exclude(exclude=task.organization)
    headers = (
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
    parameters, extra_context = table_prepare_queryset(request, headers, queryset=parameters)

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

    score_dict = {s.parameter.pk: s for s in scores_default}
    score_interact_dict = {s.parameter.pk: s for s in scores_interact}

    questionnaire = monitoring.get_questionnaire()
    if questionnaire and questionnaire.qquestion_set.exists():
        questions = questionnaire.qquestion_set.order_by("pk")
        if request.method == "POST":
            if not request.user.has_perm('exmo2010.fill_task', task):
                return HttpResponseForbidden(_('Forbidden'))
            form = QuestionnaireDynForm(request.POST, questions=questions, task=task)
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
                            answer = QAnswer.objects.get_or_create(task=task, question=question_obj)[0]
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
                                answer = QAnswer.objects.get(task=task, question=question_obj)
                            except ObjectDoesNotExist:
                                continue
                            else:
                                answer.delete()
                return HttpResponseRedirect(reverse('exmo2010:task_scores', args=[task.pk]))
        else:
            existing_answers = task.get_questionnaire_answers()
            initial_data = {}
            for a in existing_answers:
                initial_data["q_%s" % a.question.pk] = a.answer(True)
            form = QuestionnaireDynForm(questions=questions, initial=initial_data)
    else:
        form = None
    has_npa = task.organization.monitoring.has_npa
    if has_npa:
        parameters_npa = parameters.filter(npa=True)
        parameters_other = parameters.filter(npa=False)
    else:
        parameters_npa = []
        parameters_other = parameters

    _new_comment_url(request, score_dict, scores_default, parameters_npa)

    _new_comment_url(request, score_dict, scores_default, parameters_other)

    extra_context.update({
        'view_openness_perm': request.user.has_perm('exmo2010.view_openness', task),
        'score_interact_dict': score_interact_dict,
        'parameters_npa': parameters_npa,
        'parameters_other': parameters_other,
        'monitoring': monitoring,
        'task': task,
        'has_npa': has_npa,
        'title': title,
        'form': form,
        'invcodeform': SettingsInvCodeForm(),
        'show_link': request.user.is_expertA or monitoring.is_published,
    })

    return TemplateResponse(request, 'scores/task_scores.html', extra_context)


def _new_comment_url(request, score_dict, scores_default, parameters):
    """
    Get URL for new comments, if exists.

    """
    last_comments = {}

    scores = scores_default.filter(parameter_id__in=parameters)

    for param in parameters:
        score = score_dict.get(param.id, None)
        param.score = score

    if not request.user.is_anonymous() and scores:
        comments = CommentExmo.objects.filter(
            object_pk__in=scores,
            content_type__model='score',
            status=CommentExmo.OPEN,
            user__groups__name=UserProfile.organization_group,
        ).values('object_pk').annotate(pk=Max('pk'))

        for comment in comments:
            last_comments[int(comment['object_pk'])] = comment['pk']

        if last_comments:
            for param in parameters:
                score = param.score
                if not score:
                    continue

                last_comment_id = last_comments.get(score.pk, None)

                if last_comment_id and (request.user.executes(score.task) or request.user.is_expertA):
                    param.url = reverse('exmo2010:score_view', args=[score.pk]) + "#c" + str(last_comment_id)


@login_required
def score_claim_color(request, score_pk):
    """
    AJAX-вьюха для получения изображения для претензий.

    """
    score = get_object_or_404(Score, pk=score_pk)
    if request.method == "GET" and request.is_ajax():
        return TemplateResponse(request, 'claim_image.html', {'score': score})
    else:
        raise Http404


@login_required
def score_comment_unreaded(request, score_pk):
    """
    AJAX-вьюха для получения изображения для непрочитанных коментов.

    """
    score = get_object_or_404(Score, pk=score_pk)
    if request.method == "GET" and request.is_ajax():
        return TemplateResponse(request, 'commentunread_image.html', {'score': score})
    else:
        raise Http404


def rating_update(request):
    """
    AJAX-view for rating counting.

    """
    if request.method == "GET" and request.is_ajax():

        task_id = json.loads(request.GET['task_id'])

        if task_id:
            task = get_object_or_404(Task, pk=task_id)

            if request.user.has_perm('exmo2010.view_openness', task) and task.approved:
                if task.organization.monitoring.has_npa:
                    rating_types = ['all', 'other', 'npa']
                else:
                    rating_types = ['all']

                result = {}
                for rating_type in rating_types:
                    for t in task.organization.monitoring.rating(rating_type=rating_type):
                        if t.pk == task.pk:
                            result['place_' + rating_type] = t.place
                            break

                return JSONResponse(result)
            else:
                raise PermissionDenied

    raise Http404
