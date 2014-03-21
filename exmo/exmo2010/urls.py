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
import types

import reversion
from django.conf.urls import patterns, url, include
from django.core.urlresolvers import RegexURLResolver, RegexURLPattern
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

from exmo2010.views import AboutView, CertificateOrderView, HelpView, OpenDataView
from monitorings.views import MonitoringEditView, MonitoringDeleteView, MonitoringCommentReportView
from organizations.views import OrgEditView, OrgDeleteView
from parameters.views import ParamEditView, ParamDeleteView
from scores.views import ScoreAddView, ScoreEditView, ScoreDetailView
from tasks.views import AjaxTaskApproveView, AjaxTaskOpenView, AjaxTaskCloseView, TaskEditView, TaskDeleteView


def named_urls(module, *urlpatterns):
    '''
    Wrapper around django.conf.urls.patterns which can guess url name from view and
    automatically converts GenericView classes to views
    Positional args are urlpatters:
        (pattern, view, [, optional_name [, optional_kwargs]])
    If the name is omitted, it will be the same as view class or view function name
    '''
    result_patterns = []
    for urlpattern in urlpatterns:
        if isinstance(urlpattern, (RegexURLResolver, RegexURLPattern)):
            result_patterns.append(urlpattern)
            continue

        kwargs = {}
        try:
            regex, view, name, kwargs = urlpattern
        except ValueError:
            try:
                regex, view, name = urlpattern
            except ValueError:
                regex, view = urlpattern

                if isinstance(view, types.TypeType):
                    name = view.__name__
                elif isinstance(view, (str, unicode)):
                    name = view.split('.')[-1]
                else:
                    name = None

        if isinstance(view, types.TypeType):
            view = view.as_view()

        result_patterns.append(url(regex, view, kwargs=kwargs, name=name))

    return patterns(module, *result_patterns)


scores_patterns = named_urls('scores.views',
    (r'^(?P<score_pk>\d+)/$', 'score_view'),
    (r'^(?P<task_pk>\d+)_(?P<parameter_pk>\d+)/$', ScoreAddView, 'score_add'),
    (r'^(?P<score_pk>\d+)/edit/$', reversion.create_revision()(ScoreEditView.as_view()), 'score_edit'),
    (r'^(?P<score_pk>\d+)/detail/$', ScoreDetailView, 'score_detail'),
    (r'^rating_update/$', 'rating_update'),
)

scores_patterns += named_urls('',
    (r'^(?P<score_pk>\d+)/claim/create/$', 'claims.views.claim_create'),
    (r'^(?P<score_pk>\d+)/clarification/create/$', 'clarifications.views.clarification_create'),
)

monitoring_patterns = named_urls('monitorings.views',
    (r'^$', 'monitorings_list'),
    (r'^add/$', MonitoringEditView, 'monitoring_add'),
    (r'^(?P<monitoring_pk>\d+)/by_criteria_mass_export/$', 'monitoring_by_criteria_mass_export'),
    (r'^(?P<monitoring_pk>\d+)/comment_report/$', MonitoringCommentReportView, 'monitoring_comment_report'),
    (r'^(?P<monitoring_pk>\d+)/experts/$', 'monitoring_by_experts'),
    (r'^(?P<monitoring_pk>\d+)/organization_export/$', 'monitoring_organization_export'),
    (r'^(?P<monitoring_pk>\d+)/organization_import/$', 'monitoring_organization_import'),
    (r'^(?P<monitoring_pk>\d+)/parameter_export/$', 'monitoring_parameter_export'),
    (r'^(?P<monitoring_pk>\d+)/parameter_filter/$', 'monitoring_parameter_filter'),
    (r'^(?P<monitoring_pk>\d+)/parameter_found_report/$', 'monitoring_parameter_found_report'),
    (r'^(?P<monitoring_pk>\d+)/parameter_import/$', 'monitoring_parameter_import'),
    (r'^(?P<monitoring_pk>\d+)/rating/$', 'monitoring_rating'),
    (r'^(?P<monitoring_pk>\d+)/set_npa_params/$', 'set_npa_params'),
    (r'^(?P<monitoring_pk>\d+)_update/$', MonitoringEditView, 'monitoring_update'),
    (r'^(?P<monitoring_pk>\d+)_delete/$', MonitoringDeleteView, 'monitoring_delete'),
    (r'^(?P<monitoring_pk>\d+)/export/$', 'monitoring_export'),
)

monitoring_patterns += named_urls('tasks.views',
    (r'^(?P<monitoring_pk>\d+)/mass_assign_tasks/$', 'task_mass_assign_tasks'),
    (r'^(?P<monitoring_pk>\d+)/task/add/$', TaskEditView, 'task_add'),
    (r'^(?P<monitoring_pk>\d+)/tasks/$', 'tasks_by_monitoring'),
)

monitoring_patterns += named_urls('organizations.views',
    (r'^(?P<monitoring_pk>\d+)/organization/(?P<org_pk>\d+)_delete/$', OrgDeleteView, 'organization_delete'),
    (r'^(?P<monitoring_pk>\d+)/organization/(?P<org_pk>\d+)_update/$', OrgEditView, 'organization_update'),
    (r'^(?P<monitoring_pk>\d+)/organizations/$', 'organization_list'),
)

monitoring_patterns += named_urls('questionnaire.views',
    (r'^(?P<monitoring_pk>\d+)/add_questionnaire/$', 'add_questionnaire'),
    (r'^(?P<monitoring_pk>\d+)/answers_export/$', 'answers_export', 'monitoring_answers_export'),
)

monitoring_patterns += named_urls('',
    (r'^(?P<monitoring_pk>\d+)/claims/$', 'claims.views.claim_report'),
    (r'^(?P<monitoring_pk>\d+)/clarifications/$', 'clarifications.views.clarification_report'),
)


tasks_patterns = named_urls('tasks.views',
    (r'^task/(?P<task_pk>\d+)_update/$', reversion.create_revision()(TaskEditView.as_view()), 'task_update'),
    (r'^task/(?P<task_pk>\d+)_delete/$', reversion.create_revision()(TaskDeleteView.as_view()), 'task_delete'),
    (r'^task/(?P<task_pk>\d+)_ajax_approve/$', AjaxTaskApproveView, 'ajax_task_approve'),
    (r'^task/(?P<task_pk>\d+)_ajax_close/$', AjaxTaskCloseView, 'ajax_task_close'),
    (r'^task/(?P<task_pk>\d+)_ajax_open/$', AjaxTaskOpenView, 'ajax_task_open'),
    (r'^taskexport/(?P<task_pk>\d+)/$', 'task_export'),
    (r'^taskimport/(?P<task_pk>\d+)/$', 'task_import'),
)

tasks_patterns += named_urls('parameters.views',
    (r'^task/(?P<task_pk>\d+)/parameter/add/$', ParamEditView, 'parameter_add',),
    (r'^task/(?P<task_pk>\d+)/parameter/(?P<parameter_pk>\d+)_update/$', ParamEditView, 'parameter_update'),
    (r'^task/(?P<task_pk>\d+)/parameter/(?P<parameter_pk>\d+)_delete/$', ParamDeleteView, 'parameter_delete'),
    (r'^task/(?P<task_pk>\d+)/parameter/(?P<parameter_pk>\d+)_exclude/$', 'parameter_exclude'),
)


urlpatterns = named_urls('',
    (r'^$', TemplateView.as_view(template_name='index.html'), 'index'),
    (r'^accounts/', include('exmo2010.custom_registration.urls')),

    (r'^monitoring/', include(monitoring_patterns)),

    (r'^score/', include(scores_patterns)),
    (r'^scores/(?P<task_pk>\d+)/(?P<print_report_type>print|printfull)?$', 'scores.views.score_list_by_task'),

    (r'^tasks/', include(tasks_patterns)),
    (r'^task/(?P<task_pk>\d+)/history/$', 'tasks.views.task_history'),

    # Отчеты
    (r'^reports/comments/$', 'custom_comments.views.comment_list'),
    (r'^reports/clarifications/$', 'clarifications.views.clarification_list'),
    (r'^reports/claims/$', 'claims.views.claim_list'),
    (r'^reports/monitoring/$', 'monitorings.views.monitoring_report'),
    (r'^reports/monitoring/(?P<report_type>inprogress|finished)/$',
        'monitorings.views.monitoring_report', 'monitoring_report_type'),
    (r'^reports/monitoring/(?P<report_type>inprogress|finished)/(?P<monitoring_pk>\d+)/$',
        'monitorings.views.monitoring_report', 'monitoring_report_finished'),

    (r'^certificate_order/$', CertificateOrderView, 'certificate_order'),
    (r'^claim/delete/$', 'claims.views.claim_delete'),
    (r'^toggle_comment/$', 'scores.views.toggle_comment'),
    (r'^ratings/$', 'monitorings.views.ratings'),
    (r'^help/$', HelpView, 'help'),
    (r'^about/$', AboutView, 'about'),
    (r'^change_language/$', 'exmo2010.views.change_language'),

    (r'^opendata/$', OpenDataView, 'opendata'),
    (r'^feedback/$', 'exmo2010.views.feedback'),
    # AJAX-вьюха для получения списка критериев, отключенных у параметра
    (r'^get_pc/$', 'parameters.views.get_pc'),
    # AJAX-вьюха для получения кода div'а для одного вопроса (c полями).
    (r'^get_qq/$', 'questionnaire.views.get_qq'),
    # AJAX-вьюха для получения кода div'а для одного вопроса (без полей).
    (r'^get_qqt/$', 'questionnaire.views.get_qqt'),
)


def crumbs_tree(is_expert=False):
    common_tree = {
        'about': _('About'),
        'help':  _('Help'),
        'feedback': _('Feedback'),
        'opendata': _('Open data'),
        'settings': _('Settings'),
        'monitoring_report':          _('Statistics'),
        'monitoring_report_type':     _('Statistics'),
        'monitoring_report_finished': _('Statistics'),

        'auth_login': _('Log in the system'),
        'auth_password_reset':         _('Password reset (step 1 from 3)'),
        'auth_password_reset_done':    _('Password reset (step 2 from 3)'),
        'auth_password_reset_confirm': _('Password reset (step 3 from 3)'),
        'registration_register':   _('Registration (step 1 of 2)'),
        'registration_complete':   _('Registration (step 2 of 2)'),
        'registration_disallowed': _('Registration disallowed'),
        'registration_activation_complete': _('Activation complete'),
    }

    expert_tree = {
        'comment_list': _('Comments'),
        'claim_list':   _('Claims'),
        'clarification_list': _('Clarifications'),
        'ratings': _('Ratings'),

        'monitorings_list': (_('Monitoring cycles'), {
            'monitoring_add':    _('Add monitoring cycle'),
            'monitoring_delete': _('Delete monitoring cycle'),
            'monitoring_update': _('Edit monitoring cycle'),

            'add_questionnaire': _('Add questionnaire'),

            'claim_report':         _('Monitoring cycle'),
            'clarification_report': _('Monitoring cycle'),

            'monitoring_by_experts':       _('Monitoring cycle'),
            'monitoring_parameter_filter': _('Monitoring cycle'),

            'monitoring_comment_report':         _('Monitoring cycle'),
            'monitoring_parameter_found_report': _('Monitoring cycle'),

            'monitoring_parameter_import':    _('Import parameter'),
            'monitoring_organization_import': _('Import organizations'),

            'organization_list': _('Monitoring cycle'),

            'set_npa_params': _('Monitoring cycle'),

            'task_mass_assign_tasks': _('Monitoring cycle'),

            'monitoring_rating': _('Monitoring cycle'),

            'tasks_by_monitoring': (_('Monitoring cycle'), {
                'task_add':     _('Add task'),

                'organization_update':    _('Edit organization'),
                'organization_delete':    _('Delete organization'),

                'score_list_by_task': (_('Organization'), {
                    'clarification_create': _('Create clarification'),
                    'claim_create':         _('Create claim'),
                    # Task
                    'task_update':  _('Edit task'),
                    'task_delete':  _('Delete task'),
                    'task_import':  _('Import task'),
                    'task_history': _('Organization'),
                    # Score
                    'score_add':    _('Parameter'),
                    'score_view':   _('Parameter'),
                    'score_edit':   _('Parameter'),
                    # Parameter
                    'parameter_add':    _('Add parameter'),
                    'parameter_update': _('Edit parameter'),
                    'parameter_delete': _('Delete parameter'),
                })
            })
        })
    }

    nonexpert_tree = {
        'ratings': (_('Ratings'), {
            'monitoring_rating': (_('Rating'), {
                'score_list_by_task': (_('Organization'), {
                    'score_view': _('Parameter'),
                })
            }),
        }),
        'certificate_order': _('Openness certificate'),
    }

    common_tree.update(expert_tree if is_expert else nonexpert_tree)

    return {'index': ('', common_tree)}
