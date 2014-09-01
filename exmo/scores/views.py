# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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
from collections import defaultdict
from datetime import datetime

from BeautifulSoup import BeautifulSoup
from ckeditor.fields import RichTextFormField
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.forms import RadioSelect
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect, Http404, HttpResponseNotAllowed, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.html import escape, urlize
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from django.views.generic import DetailView
from livesettings import config_value

from accounts.forms import SettingsInvCodeForm
from core.response import JSONResponse
from core.templatetags.target_blank import target_blank
from core.utils import clean_message, round_ex
from custom_comments.models import CommentExmo
from exmo2010.mail import mail_comment
from exmo2010.models import Organization, Score, Task, Parameter, QAnswer, QQuestion, UserProfile
from exmo2010.models.monitoring import Monitoring
from parameters.forms import ParametersQueryForm
from perm_utils import annotate_exmo_perms
from questionnaire.forms import QuestionnaireDynForm


# The cache_control decorator will force the browser to make request to server, when user clicks 'back'
# button after add new Score. BUT, not working in Opera browser:
# (http://my.opera.com/yngve/blog/2007/02/27/introducing-cache-contexts-or-why-the).
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def score_view(request, **kwargs):
    if request.method not in ['POST', 'GET']:
        return HttpResponseNotAllowed(permitted_methods=['POST', 'GET'])

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
            score = Score.objects.get(parameter=param, task=task, revision=Score.FINAL)
        except Score.DoesNotExist:
            # OK, score does not exist and can be created.
            score = Score(parameter=param, task=task, revision=Score.FINAL)
        else:
            # User requested score creation by task and param, but score already exist.
            if request.user.has_perm('exmo2010.view_score', score):
                # Redirect user to GET score page, even if current request method is POST.
                # This way duplicate POST to create score will be ignored.
                return HttpResponseRedirect(reverse('exmo2010:score', args=[score.pk]))
            else:
                raise PermissionDenied

    org = task.organization
    param.relevant = bool(task.organization not in param.exclude.all())

    if not param.relevant and not request.user.is_expert:
        raise PermissionDenied

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
                if not Score.objects.filter(parameter=param, task=task, revision=Score.INTERIM).exists():
                    # Interim revision does not exist and should be created. It will have new pk.
                    interim_score = Score.objects.get(pk=kwargs['score_pk'])
                    last_modified = interim_score.last_modified
                    interim_score.pk = None
                    interim_score.revision = Score.INTERIM
                    interim_score.save()
                    # Restore last_modified field, that was overwritten by save()
                    Score.objects.filter(pk=interim_score.pk).update(last_modified=last_modified)

                _add_comment(request, score)
            score = form.save(commit=False)
            score.editor = request.user
            score.save()
        if org.monitoring.is_interact or org.monitoring.is_finishing:
            return HttpResponseRedirect(reverse('exmo2010:score', args=[score.pk]))
        else:
            url = reverse('exmo2010:task_scores', args=[task.pk])
            return HttpResponseRedirect('%s#parameter_%s' % (url, param.code))

    score_interim = Score.objects.filter(parameter=param, task=task, revision=Score.INTERIM)
    score_table = [{
        'label': score._meta.get_field_by_name(criterion)[0].verbose_name,
        'score': getattr(score, criterion),
        'score_interim': getattr(score_interim[0], criterion) if score_interim else '',
        'criterion': criterion,
        'max_score': getattr(score, criterion) == score._meta.get_field(criterion).choices[-1][-1]
    } for criterion in criteria]

    score_delta = score.openness - score_interim[0].openness if score_interim else 0
    if request.user.is_expert:
        show_interim_score = True
    elif request.user.is_anonymous():
        show_interim_score = False
    else:
        show_interim_score = request.user.profile.show_interim_score

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

    context = {
        'form': form,
        'score': annotate_exmo_perms(score, request.user),
        'score_interim': annotate_exmo_perms(score_interim[0] if score_interim else None, request.user),
        'param': annotate_exmo_perms(param, request.user),
        'task': annotate_exmo_perms(task, request.user),
        'org': org,
        'score_table': score_table,
        'score_delta': score_delta,
        'show_interim_score': show_interim_score,
        'masked_expert_name': _(config_value('GlobalParameters', 'EXPERT')),
        'criteria': criteria,
        'interaction': org.monitoring.is_interact or org.monitoring.is_finishing,
        'claim_list': claim_list,
        'recommendations_required': param.monitoring.no_interact is False and not all_max,
        'comment_form': score.comment_form(request.POST if request.method == 'POST' else None),
        'invcodeform': SettingsInvCodeForm(),
    }

    return TemplateResponse(request, 'scores/score.html', context)


def post_score_comment(request, score_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(permitted_methods=['POST'])

    score = get_object_or_404(Score, pk=score_pk)
    if not request.user.has_perm('exmo2010.add_comment', score):
        raise PermissionDenied

    _add_comment(request, score)
    return HttpResponseRedirect(request.POST.get('next') or reverse('exmo2010:score', args=[score.pk]))


def _add_comment(request, score):
    comment_form = score.comment_form(request.POST)
    if not comment_form.is_valid():
        # Comment is empty or request was forged.
        return

    # Replace all autoscore bricks with normal text.
    soup = BeautifulSoup(comment_form.cleaned_data['comment'])
    for input_node in soup.findAll('input'):
        input_node.replaceWith(BeautifulSoup(input_node['value']))

    comment = CommentExmo.objects.create(
        object_pk=score.pk,
        content_type=ContentType.objects.get_for_model(Score),
        user=request.user,
        comment=clean_message(unicode(soup)),
        posted_by_expert=request.user.is_expert,
        site_id=1)

    if request.user.is_expert:
        # Expert comment. Close existing org representatives comments for this score.
        org_comments = CommentExmo.objects.filter(
            object_pk=score.pk,
            status=CommentExmo.OPEN,
            user__userprofile__organization__isnull=False)

        org_comments.update(status=CommentExmo.ANSWERED, answered_date=datetime.now())
    else:
        # Org representative comment, update org status to "Active"
        org = score.task.organization
        if org.inv_status == 'RGS' and org in request.user.profile.organization.all():
            org.inv_status = 'ACT'
            org.save()

    mail_comment(request, comment)


ajax_soup = lambda txt: target_blank(urlize(escape(txt), 70)).replace('\n', '<br />')


def post_recommendations(request, score_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(permitted_methods=['POST'])

    score = get_object_or_404(Score, pk=score_pk)
    if not request.user.has_perm('exmo2010.edit_score', score):
        raise PermissionDenied

    score.recommendations = request.POST['recommendations']
    try:
        score.full_clean()
    except ValidationError:
        return HttpResponseBadRequest()
    score.save()
    return JSONResponse({'data': ajax_soup(score.recommendations)})


def post_score_links(request, score_pk):
    if request.method != 'POST':
        return HttpResponseNotAllowed(permitted_methods=['POST'])

    score = get_object_or_404(Score, pk=score_pk)
    if not request.user.has_perm('exmo2010.edit_score', score):
        raise PermissionDenied

    score.links = request.POST['links']
    score.save()
    return JSONResponse({'data': ajax_soup(score.links)})


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


class TaskScoresMixin(object):
    pk_url_kwarg = 'task_pk'
    model = Task

    def get_object(self, queryset=None):
        task = super(TaskScoresMixin, self).get_object(queryset)
        self.task = annotate_exmo_perms(task, self.request.user)
        if not self.request.user.has_perm('exmo2010.view_task', self.task):
            raise PermissionDenied

        return self.task


class TaskScoresView(TaskScoresMixin, DetailView):
    template_name = "scores/task_scores.html"

    def get_context_data(self, **kwargs):
        context = super(TaskScoresView, self).get_context_data(**kwargs)

        monitoring = self.task.organization.monitoring

        # Relevant parameters
        relevant_parameters = Parameter.objects.filter(monitoring=monitoring)\
                                               .exclude(exclude=self.task.organization)\
                                               .defer('grounds', 'rating_procedure', 'notes')
        scores_rel = Score.objects.filter(task=self.task)\
                                  .exclude(parameter__exclude=self.task.organization)\
                                  .defer('links', 'recommendations', 'created', 'last_modified', 'editor')
        relevant_parameters_exist = relevant_parameters.exists()

        # Non relevant parameters
        nonrelevant_parameters = Parameter.objects.filter(monitoring=monitoring, exclude=self.task.organization)\
                                                  .defer('grounds', 'rating_procedure', 'notes')
        scores_nonrel = Score.objects.filter(task=self.task, parameter__exclude=self.task.organization)\
                                     .defer('links', 'recommendations', 'created', 'last_modified', 'editor')
        nonrelevant_parameters_exist = nonrelevant_parameters.exists()

        # Apply user provided filters
        self.queryform = ParametersQueryForm(self.request.GET)

        if self.queryform.is_valid():
            relevant_parameters = self.queryform.apply(relevant_parameters)
            nonrelevant_parameters = self.queryform.apply(nonrelevant_parameters)

        # Set scores to relevant parameters list
        self._set_parameters_scores(relevant_parameters, scores_rel)
        self._set_last_comment_url(relevant_parameters, scores_rel)
        # Set scores to non relevant parameters list
        self._set_parameters_scores(nonrelevant_parameters, scores_nonrel)

        # Get questionnaire form
        questionnaire_form = None
        questions = QQuestion.objects.filter(questionnaire__monitoring=monitoring).order_by("pk")
        if questions:
            existing_answers = QAnswer.objects.filter(task=self.task).order_by("pk")
            initial_data = {"q_%s" % a.question.pk: a.answer(True) for a in existing_answers}
            questionnaire_form = QuestionnaireDynForm(questions=questions, initial=initial_data)

        context.update({
            'relevant_parameters': relevant_parameters,
            'nonrelevant_parameters': nonrelevant_parameters,
            'relevant_parameters_exist': relevant_parameters_exist,
            'nonrelevant_parameters_exist': nonrelevant_parameters_exist,
            'mon': monitoring,
            'task': self.task,
            'questionnaire_form': questionnaire_form,
            'invcodeform': SettingsInvCodeForm(),
            'orgs_count': Organization.objects.filter(monitoring=monitoring).count(),
            'openness': self.task.openness,
            'delta': self.task.openness - self.task.openness_initial if self.task.openness is not None else None,
        })

        return context

    @staticmethod
    def _set_parameters_scores(parameters, scores):
        score_fin_dict = {s.parameter.pk: s for s in scores if s.revision == Score.FINAL}
        score_int_dict = {s.parameter.pk: s for s in scores if s.revision == Score.INTERIM}

        for param in parameters:
            score_fin = score_fin_dict.get(param.pk, None)
            if score_fin:
                param.score_pk = score_fin.pk
                param.score_accomplished = score_fin.accomplished
                score_int = score_int_dict.get(param.pk, None)
                param.score_openness = score_fin.openness
                param.score_openness_delta = score_fin.openness - score_int.openness if score_int else 0

                criteria = ['found'] + filter(param.__getattribute__, Parameter.OPTIONAL_CRITERIONS)

                score_table = []
                for criterion in ['found'] + Parameter.OPTIONAL_CRITERIONS:
                    if criterion in criteria:
                        score_table.append({
                            'score_final': getattr(score_fin, criterion),
                            'score_interim': getattr(score_int, criterion) if score_int else '',
                            'max_score': getattr(score_fin, criterion) == score_fin._meta.get_field(criterion).choices[-1][-1]
                        })
                    else:
                        score_table.append({})

                param.score_table = score_table

    def _set_last_comment_url(self, parameters, scores):
        if self.request.user.executes(self.task) or self.request.user.is_expertA:
            scores_with_opened_comments = CommentExmo.objects.filter(
                object_pk__in=scores.values_list('pk', flat=True),
                content_type__model=ContentType.objects.get_for_model(Score),
                status=CommentExmo.OPEN,
                user__groups__name=UserProfile.organization_group,
            ).values_list('object_pk', flat=True)

            if scores_with_opened_comments:
                scores_with_opened_comments = [int(s) for s in set(scores_with_opened_comments)]
                for param in parameters:
                    if not getattr(param, 'score_pk', None):
                        continue

                    if param.score_pk in scores_with_opened_comments:
                        param.comment_url = reverse('exmo2010:score', args=[param.score_pk]) + "#last_comment"


class TaskScoresPrint(TaskScoresMixin, DetailView):
    template_name = "scores/task_scores_print.html"

    def get_context_data(self, **kwargs):
        context = super(TaskScoresPrint, self).get_context_data(**kwargs)
        task_scores_url = reverse('exmo2010:task_scores', args=(self.task.pk, ))

        context.update({
            'task': self.task,
            'task_scores_url': self.request.build_absolute_uri(task_scores_url),
        })

        return context


class RecommendationsView(TaskScoresMixin, DetailView):
    template_name = "scores/recommendations.html"

    def get_context_data(self, **kwargs):
        context = super(RecommendationsView, self).get_context_data(**kwargs)

        monitoring = self.task.organization.monitoring
        scores = list(self.task.score_set.all())

        comments_by_score = defaultdict(list)
        for comment in CommentExmo.objects.filter(object_pk__in=[s.pk for s in scores]):
            comments_by_score[int(comment.object_pk)].append(comment)

        final_scores = [s for s in scores if s.revision == Score.FINAL]
        interim_scores_by_param = dict((s.parameter.pk, s) for s in scores if s.revision == Score.INTERIM)

        param_nonrelevant = set(self.task.organization.parameter_set.values_list('pk', flat=True))
        param_relevant = monitoring.parameter_set.exclude(pk__in=param_nonrelevant)
        param_weight_sum = sum(p.weight for p in param_relevant)

        scores = []
        for score in final_scores:
            if score.pk in comments_by_score:
                score.comments = comments_by_score[score.pk]
            else:
                if score.parameter.pk in param_nonrelevant:
                    continue
                if not score.recommendations:
                    continue
            if param_weight_sum:
                interim_score = interim_scores_by_param.get(score.parameter.pk) or score
                score.interim_cost = score.parameter.weight * (100.0 - interim_score.openness) / param_weight_sum
                score.cost = round_ex(score.parameter.weight * (100.0 - score.openness) / param_weight_sum)
            else:
                score.interim_cost = score.cost = 0.0
            score.is_finished = bool(score.cost == 0 and not score.recommendations)
            score.is_relevant = bool(score.parameter.pk not in param_nonrelevant)
            scores.append(score)

        scores.sort(key=lambda s: (-s.interim_cost, s.parameter.code))

        context.update({
            'scores': annotate_exmo_perms(scores, self.request.user),
            'mon': monitoring,
            'orgs_count': monitoring.organization_set.count(),
            'registered_count': monitoring.organization_set.filter(inv_status__in=('RGS', 'ACT')).count(),
            'openness': self.task.openness,
            'masked_expert_name': _(config_value('GlobalParameters', 'EXPERT')),
        })

        if context['openness'] is None:
            context.update(total_cost=None, delta=None)
        else:
            context.update({
                'total_cost': round_ex(100.0 - float(context['openness'])),
                'delta': context['openness'] - self.task.openness_initial
            })

        return context


class RecommendationsPrint(RecommendationsView):
    template_name = "scores/recommendations_print.html"
    with_comments = False

    def get_context_data(self, **kwargs):
        context = super(RecommendationsPrint, self).get_context_data(**kwargs)
        recommendations_url = reverse('exmo2010:recommendations', args=(self.task.pk,))
        rating_place = None
        if self.task.approved:
            for t in self.task.organization.monitoring.rating(rating_type='all'):
                if t.pk == self.task.pk:
                    rating_place = t.place
                    break

        context.update({
            'rating_place': rating_place,
            'recommendations_url': self.request.build_absolute_uri(recommendations_url),
        })

        return context


class RecommendationsPrintWithComments(RecommendationsPrint):
    with_comments = True

    def get_object(self, queryset=None):
        task = super(RecommendationsPrintWithComments, self).get_object(queryset)
        if not self.request.user.has_perm('exmo2010.view_comments', task):
            raise PermissionDenied
        return task


def rating_update(request):
    """
    AJAX-view for rating counting.

    """
    if request.method == "GET" and request.is_ajax():
        task = get_object_or_404(Task, pk=request.GET.get('task_id', None))

        if request.user.has_perm('exmo2010.view_openness', task) and task.approved:
            place = None
            for t in task.organization.monitoring.rating(rating_type='all'):
                if t.pk == task.pk:
                    place = t.place
                    break

            return JSONResponse({'rating_place': place})
        else:
            raise PermissionDenied

    raise Http404
