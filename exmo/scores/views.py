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

import datetime
import json

import reversion
from django.contrib.auth.decorators import login_required
from django.contrib.comments import signals
from django.contrib.comments.views.comments import post_comment
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse
from django.db.models import Max
from django.dispatch import Signal
from django.forms.util import ErrorList
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils import simplejson
from django.utils.decorators import method_decorator
from django.utils.text import get_text_list
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.detail import DetailView
from livesettings import config_value

from accounts.forms import SettingsInvCodeForm
from bread_crumbs.views import breadcrumbs
from core.helpers import table_prepare_queryset
from claims.forms import ClaimAddForm
from clarifications.forms import ClarificationAddForm
from custom_comments.models import CommentExmo
from custom_comments.signals import comment_notification
from exmo2010.models import Claim, Clarification, MonitoringInteractActivity, Parameter, QAnswer, QQuestion
from exmo2010.models import Score, Task, UserProfile, MONITORING_PUBLISHED, MONITORING_INTERACTION, MONITORING_FINALIZING
from questionnaire.forms import QuestionnaireDynForm
from scores.forms import ScoreForm, ScoreFormWithComment


URL_LENGTH = 70  # Length to truncate URLs to


class ScoreMixin(object):
    model = Score
    form_class = ScoreForm
    context_object_name = "object"
    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super(ScoreMixin, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

    def get_redirect(self, request):
        redirect = "%s?%s#parameter_%s" % (reverse('exmo2010:score_list_by_task',
                                           args=[self.object.task.pk]),
                                           request.GET.urlencode(),
                                           self.object.parameter.code)
        return redirect.replace("%", "%%")


class ScoreAddView(ScoreMixin, CreateView):
    template_name = "form.html"

    def get_redirect(self, request):
        redirect = "%s?%s#parameter_%s" % (reverse('exmo2010:score_list_by_task',
                                           args=(self.task.pk,)),
                                           request.GET.urlencode(),
                                           self.parameter.code)
        redirect = redirect.replace("%", "%%")

        return redirect

    def get(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=args[0])
        self.parameter = get_object_or_404(Parameter, pk=args[1])

        try:
            score = Score.objects.get(parameter=self.parameter, task=self.task)
        except Score.DoesNotExist:
            pass
        else:
            return HttpResponseRedirect(reverse('exmo2010:score_view', args=(score.pk,)))

        if not request.user.has_perm('exmo2010.fill_task', self.task):
            return HttpResponseForbidden(_('Forbidden'))

        self.initial = {
            'task': self.task,
            'parameter': self.parameter
        }
        result = super(ScoreAddView, self).get(request, *args, **kwargs)

        return result

    def post(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=args[0])
        self.parameter = get_object_or_404(Parameter, pk=args[1])
        self.success_url = self.get_redirect(request)
        result = super(ScoreAddView, self).post(request, *args, **kwargs)

        return result

    def get_context_data(self, **kwargs):
        context = super(ScoreAddView, self).get_context_data(**kwargs)
        request = self.request
        task = self.task
        parameter = self.parameter
        title = u'%(code)s \u2014 %(name)s' % {'code': parameter.code, 'name': parameter.name}

        expert = _(config_value('GlobalParameters', 'EXPERT'))
        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        breadcrumbs(request, crumbs, task)
        current_title = _('Parameter')

        extra_context = {
            'current_title': current_title,
            'expert': expert,
            'parameter': parameter,
            'task': task,
            'title': title,
        }
        context.update(extra_context)

        return context


class ScoreDeleteView(ScoreMixin, DeleteView):
    template_name = "exmo2010/score_confirm_delete.html"

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ScoreDeleteView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        title = _('Delete score %s') % self.object.parameter
        if not request.user.has_perm('exmo2010.delete_score', self.object):
            return HttpResponseForbidden(_('Forbidden'))
        else:
            self.extra_context = {'current_title': title}
        return super(ScoreDeleteView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.success_url = self.get_redirect(request)
        return super(ScoreDeleteView, self).post(request, *args, **kwargs)


class ScoreEditView(UpdateView):
    form_class = ScoreForm
    template_name = "form.html"
    model = Score
    extra_context = {}
    is_interaction_or_finalizing = False

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        score = get_object_or_404(Score, pk=kwargs['pk'])

        if not request.user.has_perm('exmo2010.edit_score', score):
            return HttpResponseForbidden(_('Forbidden'))

        if score.parameter.monitoring.status in [MONITORING_INTERACTION, MONITORING_FINALIZING]:
            self.form_class = ScoreFormWithComment
            self.template_name = "form_with_comment.html"
            self.is_interaction_or_finalizing = True
        result = super(ScoreEditView, self).dispatch(request, *args, **kwargs)

        return result

    def get_initial(self):
        if self.is_interaction_or_finalizing:
            self.object = self.get_object()
            initial = self.object.__dict__.copy()
            if 'comment' in initial:
                recomendation = initial.pop('comment')
                initial['recomendation'] = recomendation

            result = {
                'instance': self.object,
                'initial': initial
            }
        else:
            result = super(ScoreEditView, self).get_initial()

        return result

    def get_form_kwargs(self):
        if self.is_interaction_or_finalizing:
            result = self.get_initial()
            if self.request.method in ('POST', 'PUT'):
                result.update({
                    'data': self.request.POST,
                })
        else:
            result = super(ScoreEditView, self).get_form_kwargs()

        return result

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.success_url = self.get_redirect(request)

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        self.valid = True
        try:
            signal_to_create_revision.send(
                sender=Score.__class__,
                instance=self.object,
            )
        except ValidationError:
            self.valid = False

        if form.is_valid() and self.valid:
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        if self.is_interaction_or_finalizing:
            button = self.request.POST['tabs']
            if button in ['submit_comment', 'submit_score_and_comment']:
                post_comment(self.request)

            message = _('Changed %s.') % get_text_list(form.changed_data, _('and'))
            reversion.revision.comment = message

        result = super(ScoreEditView, self).form_valid(form)

        return result

    def form_invalid(self, form):
        if not self.valid:
            error = form._errors.setdefault('__all__', ErrorList())
            error.append(_('Couldn`t save a new version of the existing score since the existing score is incomplete. '
                           'Contact your Supervisor.'))
        return super(ScoreEditView, self).form_invalid(form)

    def get_redirect(self, request):
        if self.is_interaction_or_finalizing:
            result = reverse('exmo2010:score_view', args=[self.object.pk])
        else:
            redirect = "%s?%s#parameter_%s" % (reverse('exmo2010:score_list_by_task',
                                               args=[self.object.task.pk]),
                                               request.GET.urlencode(),
                                               self.object.parameter.code)
            result = redirect.replace("%", "%%")

        return result

    def get_context_data(self, **kwargs):
        context = super(ScoreEditView, self).get_context_data(**kwargs)
        current_title = _('Parameter')
        parameter = self.object.parameter
        task = self.object.task
        title = u'%(code)s \u2014 %(name)s' % {'code': parameter.code, 'name': parameter.name}

        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        breadcrumbs(self.request, crumbs, task)

        extra_context = {
            'current_title': current_title,
            'is_interaction_or_finalizing': self.is_interaction_or_finalizing,
            'parameter': parameter,
            'task': task,
            'title': title,
            'url_length': URL_LENGTH,
        }
        context.update(extra_context)

        all_score_claims = Claim.objects.filter(score=self.object)
        if not self.request.user.profile.is_expertA:
            all_score_claims = all_score_claims.filter(addressee=self.object.task.user)
        all_score_clarifications = Clarification.objects.filter(score=self.object)

        self.extra_context = {
            'claim_form': ClaimAddForm(prefix="claim"),
            'claim_list': all_score_claims,
            'clarification_form': ClarificationAddForm(prefix="clarification"),
            'clarification_list': all_score_clarifications,
        }
        context.update(self.extra_context)

        return context


signals.comment_was_posted.connect(comment_notification, sender=CommentExmo)


class ScoreDetailView(ScoreMixin, DetailView):
    template_name = "detail.html"

    def dispatch(self, request, *args, **kwargs):
        score = get_object_or_404(Score, pk=kwargs['pk'])

        if not request.user.has_perm('exmo2010.view_score', score):
            return HttpResponseForbidden(_('Forbidden'))

        result = super(ScoreDetailView, self).dispatch(request, *args, **kwargs)

        return result

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.success_url = self.get_redirect(request)

        current_title = _('Parameter')
        if request.user.is_active and request.user.profile.is_expertA:
            all_score_claims = Claim.objects.filter(score=self.object)
        else:
            all_score_claims = Claim.objects.filter(score=self.object, addressee=self.object.task.user)
        all_score_clarifications = Clarification.objects.filter(score=self.object)
        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        breadcrumbs(request, crumbs, self.object.task)

        parameter = self.object.parameter
        title = u'%(code)s \u2014 %(name)s' % {'code': parameter.code, 'name': parameter.name}
        time_to_answer = self.object.task.organization.monitoring.time_to_answer
        delta = datetime.timedelta(days=time_to_answer)
        today = datetime.date.today()
        peremptory_day = today + delta
        expert = _(config_value('GlobalParameters', 'EXPERT'))

        self.extra_context = {
            'claim_form': ClaimAddForm(prefix="claim"),
            'claim_list': all_score_claims,
            'clarification_form': ClarificationAddForm(prefix="clarification"),
            'clarification_list': all_score_clarifications,
            'current_title': current_title,
            'expert': expert,
            'invcodeform': SettingsInvCodeForm(),
            'parameter': parameter,
            'peremptory_day': peremptory_day,
            'task': self.object.task,
            'title': title,
            'url_length': URL_LENGTH,
            'view': True,
        }

        result = super(ScoreDetailView, self).get(request, *args, **kwargs)

        return result


def score_manager(request, score_id, method='update'):
    if method == 'delete':
        redirect_url = reverse('exmo2010:score_delete', args=[score_id])
        return HttpResponseRedirect(redirect_url)
    elif method == 'update':
        redirect_url = reverse('exmo2010:score_edit', args=[score_id])
        return HttpResponseRedirect(redirect_url)
    elif method == 'view':
        redirect_url = reverse('exmo2010:score_detail', args=[score_id])
        return HttpResponseRedirect(redirect_url)

    return HttpResponseForbidden(_('Forbidden'))


def score_view(request, score_id):
    score = get_object_or_404(Score, pk=score_id)

    if request.user.has_perm('exmo2010.edit_score', score):
        call_view = ScoreEditView.as_view()
        revision = reversion.create_revision()
        callback = revision(call_view)
        result = callback(request, pk=score_id)

    elif request.user.has_perm('exmo2010.view_score', score):
        call_view = ScoreDetailView.as_view()
        result = call_view(request, pk=score_id)

    else:
        result = HttpResponseForbidden(_('Forbidden'))

    return result


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
    title = task.organization.name
    if not request.user.has_perm('exmo2010.view_task', task):
        return HttpResponseForbidden(_('Forbidden'))
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

    score_dict = {}
    score_interact_dict = {}

    for score in scores_default:
        score_dict[score.parameter.pk] = score

    for score in scores_interact:
        score_interact_dict[score.parameter.pk] = score

    current_title = _('Organization')
    if report:
        # Print report
        extra_context.update(
            {
                'score_dict': score_dict,
                'parameters': parameters,
                'task': task,
                'current_title': current_title,
                'title': title,
                'report': report,
            }
        )

        crumbs = ['Home', 'Monitoring', 'Organization']
        breadcrumbs(request, crumbs, task)

        return render_to_response(
            'task_report.html',
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
                    return HttpResponseRedirect(reverse(
                        'exmo2010:score_list_by_task', args=[task.pk]))
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

        # Не показываем ссылку экспертам B или предатвителям, если статус
        # мониторинга отличается от "Опубликован".
        user = request.user
        if (not user.is_active or
            (user.profile.is_expertB and not user.profile.is_expertA) or
            user.profile.is_organization) and \
           (monitoring.status != MONITORING_PUBLISHED) and not user.is_superuser:
            show_link = False
        else:
            show_link = True
        extra_context.update(
            {
                'score_interact_dict': score_interact_dict,
                'parameters_npa': parameters_npa,
                'parameters_other': parameters_other,
                'monitoring': monitoring,
                'task': task,
                'has_npa': has_npa,
                'current_title': current_title,
                'title': title,
                'form': form,
                'invcodeform': SettingsInvCodeForm(),
                'show_link': show_link,
            }
        )

        crumbs = ['Home', 'Monitoring', 'Organization']
        breadcrumbs(request, crumbs, task)

        return render_to_response(
            'score_list.html',
            extra_context,
            context_instance=RequestContext(request),
        )


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

                if last_comment_id:
                    if request.user.profile.is_expertB and score.task.user_id == request.user.id or \
                            request.user.profile.is_expertA:
                        param.url = reverse('exmo2010:score_view', args=[score.pk]) + "#c" + str(last_comment_id)


@csrf_protect
@login_required
def score_add_comment(request, score_id):
    score = get_object_or_404(Score, pk=score_id)
    title = _('Add new parameter')
    if request.user.has_perm('exmo2010.add_comment_score', score):

        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList', 'ScoreView']
        breadcrumbs(request, crumbs, score)
        current_title = _('Add parameter')

        return render_to_response(
            'score_comment_form.html',
            {
                'score': score,
                'current_title': current_title,
                'title': title,
            },
            context_instance=RequestContext(request),
        )
    else:
        return HttpResponseForbidden(_('Forbidden'))


def log_user_activity(comment, **kwargs):
    """
    Signal handler. Organizations representatives activity log at the stage of interaction.

    """
    score = Score.objects.get(pk=comment.object_pk)
    monitoring = score.task.organization.monitoring
    user = comment.user
    if monitoring.is_interact and user.profile.is_organization and not user.is_superuser:
        MonitoringInteractActivity.objects.get_or_create(monitoring=monitoring, user=user)

signals.comment_was_posted.connect(log_user_activity, sender=CommentExmo)


def create_revision(sender, instance, **kwargs):
    """
    Сохранение ревизии оценки на стадии взаимодействия.

    """
    if instance.revision != Score.REVISION_INTERACT:
        instance.create_revision(Score.REVISION_INTERACT)

signal_to_create_revision = Signal(providing_args=["instance"])
signal_to_create_revision.connect(create_revision)


@login_required
def score_claim_color(request, score_id):
    """
    AJAX-вьюха для получения изображения для претензий.

    """
    score = get_object_or_404(Score, pk=score_id)
    if request.method == "GET" and request.is_ajax():
        return render_to_response('claim_image.html',
                                  {'score': score},
                                  context_instance=RequestContext(request))
    else:
        raise Http404


@login_required
def score_comment_unreaded(request, score_id):
    """
    AJAX-вьюха для получения изображения для непрочитанных коментов.

    """
    score = get_object_or_404(Score, pk=score_id)
    if request.method == "GET" and request.is_ajax():
        return render_to_response('commentunread_image.html',
                                  {'score': score},
                                  context_instance=RequestContext(request))
    else:
        raise Http404


def ratingUpdate(request):
    """
    AJAX-view for rating counting.

    """
    rating = {}
    if request.method == "GET" and request.is_ajax():

        task_id = json.loads(request.GET['task_id'])

        if task_id:
            task = get_object_or_404(Task, pk=task_id)
            rating_names = dict(request.GET)['rating_names']

            for item in rating_names:
                attr = 'rating_' + item
                rating[item] = getattr(task, attr)

            return HttpResponse(json.dumps(rating), mimetype='application/json')
    else:
        raise Http404
