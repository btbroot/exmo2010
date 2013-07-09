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

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.comments.signals import comment_was_posted
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db.models import Max, Q
from django.db.models.signals import pre_save
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
from reversion import revision

from accounts.forms import SettingsInvCodeForm
from bread_crumbs.views import breadcrumbs
from core.helpers import table_prepare_queryset
from core.tasks import send_email
from claims.forms import ClaimAddForm
from clarifications.forms import ClarificationAddForm
from custom_comments.models import CommentExmo
from exmo2010.models import Claim, Clarification, MonitoringInteractActivity, Parameter
from exmo2010.models import QAnswer, QQuestion, Score, Task, UserProfile, MONITORING_PUBLISH
from scores.forms import ScoreForm
from questionnaire.forms import QuestionnaireDynForm


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


class LoginRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class ScoreAddView(ScoreMixin, CreateView):
    template_name = "form.html"

    def get_redirect(self, request, task, parameter):
        redirect = "%s?%s#parameter_%s" % (reverse('exmo2010:score_list_by_task',
                                           args=(task.pk,)),
                                           request.GET.urlencode(),
                                           parameter.code)
        redirect = redirect.replace("%", "%%")
        return redirect

    def get(self, request, *args, **kwargs):
        task = get_object_or_404(Task, pk=args[0])
        parameter = get_object_or_404(Parameter, pk=args[1])
        title = parameter

        try:
            score = Score.objects.get(parameter=parameter, task=task)
        except Score.DoesNotExist:
            pass
        else:
            return HttpResponseRedirect(reverse('exmo2010:score_view', args=(score.pk,)))

        if not request.user.has_perm('exmo2010.fill_task', task):
            return HttpResponseForbidden(_('Forbidden'))

        self.success_url = self.get_redirect(request, task, parameter)

        self.initial = {'task': task, 'parameter': parameter}

        expert = _(config_value('GlobalParameters', 'EXPERT'))

        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        breadcrumbs(request, crumbs, task)
        current_title = _('Parameter')

        self.extra_context = {
            'task': task,
            'expert': expert,
            'parameter': parameter,
            'current_title': current_title,
            'title': title,
        }

        return super(ScoreAddView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=args[0])
        self.parameter = get_object_or_404(Parameter, pk=args[1])
        self.success_url = self.get_redirect(request, self.task, self.parameter)
        return super(ScoreAddView, self).post(request, *args, **kwargs)

    def form_invalid(self, form):
        self.extra_context = {
            'task': self.task,
            'parameter': self.parameter,
        }
        return super(ScoreAddView, self).form_invalid(form)


class ScoreDeleteView(LoginRequiredMixin, ScoreMixin, DeleteView):
    template_name = "exmo2010/score_confirm_delete.html"

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


class ScoreEditView(LoginRequiredMixin, ScoreMixin, UpdateView):
    template_name = "form.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.user.has_perm('exmo2010.edit_score', self.object):
            current_title = _('Parameter')
            if request.user.is_active and request.user.profile.is_expertA:
                all_score_claims = Claim.objects.filter(score=self.object)
            else:
                all_score_claims = Claim.objects.filter(score=self.object, addressee=self.object.task.user)
            all_score_clarifications = Clarification.objects.filter(score=self.object)
            crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
            breadcrumbs(request, crumbs, self.object.task)

            title = _('%s') % self.object.parameter
            self.extra_context = {
                'task': self.object.task,
                'parameter': self.object.parameter,
                'current_title': current_title,
                'title': title,
                'claim_list': all_score_claims,
                'clarification_list': all_score_clarifications,
                'claim_form': ClaimAddForm(prefix="claim"),
                'clarification_form': ClarificationAddForm(
                    prefix="clarification"),
            }
        else:
            return HttpResponseForbidden(_('Forbidden'))

        return super(ScoreEditView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ScoreForm(request.POST, instance=self.object)
        message = _construct_change_message(request, form, None)
        revision.comment = message

        if self.object.active_claim:
            if not (form.is_valid() and form.changed_data):
                return HttpResponse(_('Have active claim, but no data changed'))

        self.success_url = self.get_redirect(request)
        return super(ScoreEditView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        result = super(ScoreEditView, self).form_valid(form)
        score_change_notify(self, form)
        return result

    def form_invalid(self, form):
        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
        breadcrumbs(self.request, crumbs, self.object.task)
        title = _('%s') % self.object.parameter
        current_title = _('Parameter')

        self.extra_context = {
            'task': self.object.task,
            'parameter': self.object.parameter,
            'current_title': current_title,
            'title': title,
        }
        return super(ScoreEditView, self).form_invalid(form)


class ScoreDetailView(ScoreMixin, DetailView):
    template_name = "detail.html"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.success_url = self.get_redirect(request)

        if request.user.has_perm('exmo2010.view_score', self.object):
            current_title = _('Parameter')
            if request.user.is_active and request.user.profile.is_expertA:
                all_score_claims = Claim.objects.filter(score=self.object)
            else:
                all_score_claims = Claim.objects.filter(score=self.object, addressee=self.object.task.user)
            all_score_clarifications = Clarification.objects.filter(score=self.object)
            crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
            breadcrumbs(request, crumbs, self.object.task)

            self.template_name = "detail.html"
            title = _('Score for parameter "%s"') % self.object.parameter.name
            time_to_answer = self.object.task.organization.monitoring.time_to_answer
            delta = datetime.timedelta(days=time_to_answer)
            today = datetime.date.today()
            peremptory_day = today + delta
            expert = _(config_value('GlobalParameters', 'EXPERT'))

            self.extra_context = {'current_title': current_title,
                                  'title': title,
                                  'task': self.object.task,
                                  'parameter': self.object.parameter,
                                  'claim_list': all_score_claims,
                                  'clarification_list': all_score_clarifications,
                                  'peremptory_day': peremptory_day,
                                  'expert': expert,
                                  'view': True,
                                  'invcodeform': SettingsInvCodeForm(),
                                  'claim_form': ClaimAddForm(prefix="claim"),
                                  'clarification_form': ClarificationAddForm(prefix="clarification"), }

        return super(ScoreDetailView, self).get(request, *args, **kwargs)


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
        redirect_url = reverse('exmo2010:score_edit', args=[score_id])
        return HttpResponseRedirect(redirect_url)
    if request.user.has_perm('exmo2010.view_score', score):
        redirect_url = reverse('exmo2010:score_detail', args=[score_id])
        return HttpResponseRedirect(redirect_url)

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
    title = _('%s') % task.organization.name
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
           (monitoring.status != MONITORING_PUBLISH) and not user.is_superuser:
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

    if scores:
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
    title = _('Add new comment')
    if request.user.has_perm('exmo2010.add_comment_score', score):

        crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList', 'ScoreView']
        breadcrumbs(request, crumbs, score)
        current_title = _('Add comment')

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


def log_user_activity(**kwargs):
    """
    Oбработчик сигнала при создании нового комментария. Функция для ведения журнала посещений представителя
    организации на стадии взаимодействия.

    """
    comment = kwargs['comment']
    if comment.content_type.model == 'score':
        score = Score.objects.get(pk=comment.object_pk)
        monitoring = score.task.organization.monitoring
        user = comment.user
        if monitoring.is_interact and user.profile.is_organization and not user.is_superuser:
            activity = MonitoringInteractActivity.objects.filter(monitoring=monitoring, user=user).exists()
            if activity:
                log = MonitoringInteractActivity(monitoring=monitoring, user=user)
                try:
                    log.save()
                except IntegrityError:
                    pass


def score_change_notify(self, form):
    """
    Scores changing notification.

    """
    changes = []
    score = form.instance
    task = score.task
    if form.changed_data:
        for change in form.changed_data:
            change_dict = {'field': change,
                           'was': form.initial.get(change, form.fields[change].initial),
                           'now': form.cleaned_data[change]}
            changes.append(change_dict)

    if task.approved:
        rcpts = User.objects.filter(
            Q(userprofile__organization=task.organization) |
            Q(groups__name=UserProfile.expertA_group) |
            Q(is_superuser=True),
            userprofile__preference__icontains='"notify_score": {"type": 1}',
            is_active=True, email__isnull=False,
        ).distinct().values_list('email', flat=True)
        rcpts = list(rcpts)

        if task.user.userprofile.notify_score_preference['type'] == UserProfile.NOTIFICATION_TYPE_ONEBYONE:
            rcpts.append(task.user.email)

        subject = _('%(prefix)s%(monitoring)s - %(org)s: %(code)s - Score changed') % {
            'prefix': config_value('EmailServer', 'EMAIL_SUBJECT_PREFIX'),
            'monitoring': task.organization.monitoring,
            'org': task.organization.name.split(':')[0],
            'code': score.parameter.code,
        }

        current_site = Site.objects.get_current()
        url = '%s://%s%s' % (self.request.is_secure() and 'https' or 'http', current_site,
                             reverse('exmo2010:score_view', args=[score.pk]))
        c = {
            'score': score,
            'url': url,
            'changes': changes,
            'subject': subject
        }

        for rcpt in rcpts:
            send_email.delay(rcpt, subject, 'score_email', context=c)


def create_revision(sender, instance, using, **kwargs):
    """
    Сохранение ревизии оценки на стадии взаимодействия.

    """
    if instance.revision != Score.REVISION_INTERACT:
        instance.create_revision(Score.REVISION_INTERACT)


pre_save.connect(create_revision, sender=Score)


def _construct_change_message(request, form, formsets):
        """
        Construct a change message from a changed object. Можно использовать для reversion.

        """
        change_message = []
        if form.changed_data:
            change_message.append(_('Changed %s.') % get_text_list(form.changed_data, _('and')))

        if formsets:
            for formset in formsets:
                for added_object in formset.new_objects:
                    change_message.append(_('Added %(name)s "%(object)s".')
                                          % {'name': force_unicode(added_object._meta.verbose_name),
                                             'object': force_unicode(added_object)})
                for changed_object, changed_fields in formset.changed_objects:
                    change_message.append(_('Changed %(list)s for %(name)s "%(object)s".')
                                          % {'list': get_text_list(changed_fields, _('and')),
                                             'name': force_unicode(changed_object._meta.verbose_name),
                                             'object': force_unicode(changed_object)})
                for deleted_object in formset.deleted_objects:
                    change_message.append(_('Deleted %(name)s "%(object)s".')
                                          % {'name': force_unicode(deleted_object._meta.verbose_name),
                                             'object': force_unicode(deleted_object)})
        change_message = ' '.join(change_message)
        return change_message or _('No fields changed.')


@login_required
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


# Регистрируем обработчик сигнала.
comment_was_posted.connect(log_user_activity)
