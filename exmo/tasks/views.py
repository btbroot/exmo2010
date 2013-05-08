# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
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
import csv
import re
import string

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.models import Group, User
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response
from django.template import loader, Context, RequestContext
from django.utils.translation import ugettext as _
from django.views.generic.edit import ProcessFormView, ModelFormMixin
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from livesettings import config_value
import reversion

from accounts.forms import SettingsInvCodeForm
from bread_crumbs.views import breadcrumbs
from core.utils import UnicodeReader, UnicodeWriter
from exmo2010.models import Monitoring, Organization, Parameter, Score, Task, TaskHistory
from core.helpers import table
from tasks.forms import TaskForm


def task_export(request, id):
    task = get_object_or_404(Task, pk=id)
    if not request.user.has_perm('exmo2010.view_task', task):
        return HttpResponseForbidden(_('Forbidden'))
    parameters = Parameter.objects.filter(monitoring=task.organization.monitoring).exclude(exclude=task.organization)
    scores = Score.objects.filter(task=id, revision=Score.REVISION_DEFAULT)
    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=task-%s.csv' % id
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)
    writer.writerow([
        '#Code',
        'Name',
        'Found',
        'Complete',
        'CompleteComment',
        'Topical',
        'TopicalComment',
        'Accessible',
        'AccessibleComment',
        'Hypertext',
        'HypertextComment',
        'Document',
        'DocumentComment',
        'Image',
        'ImageComment',
        'Comment'
    ])
    category = None
    subcategory = None
    for p in parameters:
        out = (
            p.code,
            p.name,
        )
        try:
            s = scores.get(parameter=p)
        except:
            out += (
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                '',
                ''
            )
        else:
            out += (s.found,)
            if p.complete:
                out += (
                    s.complete,
                    s.completeComment
                )
            else:
                out += ('', '')
            if p.topical:
                out += (
                    s.topical,
                    s.topicalComment
                )
            else:
                out += ('', '')
            if p.accessible:
                out += (
                    s.accessible,
                    s.accessibleComment
                )
            else:
                out += ('', '')
            if p.hypertext:
                out += (
                    s.hypertext,
                    s.hypertextComment
                )
            else:
                out += ('', '')
            if p.document:
                out += (
                    s.document,
                    s.documentComment
                )
            else:
                out += ('', '')
            if p.image:
                out += (
                    s.image,
                    s.imageComment
                )
            else:
                out += ('','')
            out += (s.comment,)
        writer.writerow(out)
    return response


@reversion.create_revision
@login_required
def task_import(request, id):
    task = get_object_or_404(Task, pk=id)
    if not request.user.has_perm('exmo2010.fill_task', task):
        return HttpResponseForbidden(_('Forbidden'))
    if not request.FILES.has_key('taskfile'):
        return HttpResponseRedirect(reverse('exmo2010:score_list_by_task', args=[id]))
    reader = UnicodeReader(request.FILES['taskfile'])
    errLog = []
    rowOKCount = 0
    rowALLCount = 0
    try:
        for row in reader:
            rowALLCount += 1
            if row[0].startswith('#'):
                errLog.append(_("row %d. Starts with '#'. Skipped") % reader.line_num)
                continue
            try:
                code = re.match('^(\d+)$', row[0])
                if not code:
                  errLog.append(_("row %(row)d (csv). Not a code: %(raw)s") % {'row': reader.line_num, 'raw': row[0]})
                  continue
                if (
                    row[2]  == '' and
                    row[3]  == '' and
                    row[4]  == '' and
                    row[5]  == '' and
                    row[6]  == '' and
                    row[7]  == '' and
                    row[8]  == '' and
                    row[9]  == '' and
                    row[10] == '' and
                    row[11] == '' and
                    row[12] == '' and
                    row[13] == '' and
                    row[14] == '' and
                    row[15] == ''
                  ):
                    errLog.append(_("row %(row)d (csv). Empty score: %(raw)s") % {'row': reader.line_num, 'raw': row[0]})
                    continue
                parameter = Parameter.objects.get(code=code.group(1), monitoring = task.organization.monitoring)
                try:
                    score = Score.objects.get(task = task, parameter = parameter)
                except Score.DoesNotExist:
                    score = Score()
                score.task              = task
                score.parameter         = parameter
                score.found             = row[2]
                score.complete          = row[3]
                score.completeComment   = row[4]
                score.topical           = row[5]
                score.topicalComment    = row[6]
                score.accessible        = row[7]
                score.accessibleComment = row[8]
                score.hypertext         = row[9]
                score.hypertextComment  = row[10]
                score.document          = row[11]
                score.documentComment   = row[12]
                score.image             = row[13]
                score.imageComment      = row[14]
                score.comment           = row[15]
                score.full_clean()
                score.save()
            except ValidationError, e:
                errLog.append(_("row %(row)d (validation). %(raw)s") % {
                    'row': reader.line_num,
                    'raw': '; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()])})
            except Parameter.DoesNotExist:
                errLog.append(_("row %(row)d. %(raw)s") % {
                    'row': reader.line_num,
                    'raw': _('Parameter matching query does not exist')})
            except Exception, e:
                errLog.append(_("row %(row)d. %(raw)s") % {
                    'row': reader.line_num,
                    'raw': filter(lambda x: x in string.printable, e.__str__())})
            else:
                rowOKCount += 1
    except csv.Error, e:
        errLog.append(_("row %(row)d (csv). %(raw)s") % {'row':reader.line_num, 'raw':e})
    title = _('Import CSV for task %s') % task

    crumbs = ['Home', 'Monitoring', 'Organization', 'ScoreList']
    breadcrumbs(request, crumbs, task)
    current_title = _('Import task')

    return render_to_response(
        'task_import_log.html',
        {
            'task': task,
            'file': request.FILES['taskfile'],
            'errLog': errLog,
            'rowOKCount': rowOKCount,
            'rowALLCount': rowALLCount,
            'current_title': current_title,
            'title': title,
        },
        context_instance=RequestContext(request),
    )


def tasks(request):
    return HttpResponseRedirect(reverse('exmo2010:monitoring_list'))


def tasks_by_monitoring_and_organization(request, monitoring_id, organization_id):
    """
    We have 3 generic group: experts, customers, organizations.
    Superusers: all tasks
    Experts: only own tasks
    Customers: all approved tasks
    organizations: all approved tasks of organizations that belongs to user
    Also for every ogranization we can have group.

    """
    monitoring = get_object_or_404(Monitoring, pk = monitoring_id)
    organization = get_object_or_404(Organization, pk = organization_id)
    user = request.user
    profile = None
    if user.is_active: profile = user.profile
    if not user.has_perm('exmo2010.view_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Task list for %s') % organization.name
    queryset = Task.objects.filter(organization = organization)
    # Or, filtered by user
    if user.has_perm('exmo2010.admin_monitoring', monitoring):
      headers = (
                (_('organization'), 'organization__name', 'organization__name', None, None),
                (_('expert'), 'user__username', 'user__username', None, None),
                (_('status'), 'status', 'status', int, Task.TASK_STATUS),
                (_('complete, %'), None, None, None, None),
                (_('openness, %'), None, None, None, None),
      )
    elif profile and profile.is_expert:
    # Or, without Expert
      headers = (
                (_('organization'), 'organization__name', 'organization__name', None, None),
                (_('status'), 'status', 'status', int, Task.TASK_STATUS),
                (_('complete, %'), None, None, None, None),
                (_('openness, %'), None, None, None, None)
      )
    else:
      queryset = Task.approved_tasks.all()
      queryset = queryset.filter(organization = organization)
      headers = (
                (_('organization'), 'organization__name', 'organization__name', None, None),
                (_('openness, %'), None, None, None, None)
              )
    task_list = []
    for task in queryset:
        if user.has_perm('exmo2010.view_task', task): task_list.append(task.pk)
    queryset = Task.objects.filter(pk__in = task_list)

    crumbs = ['Home', 'Monitoring', 'Organization']
    breadcrumbs(request, crumbs, monitoring)
    current_title = _('Organization')

    return table(request, headers, queryset=queryset, paginate_by=15,
                 extra_context={
                     'monitoring': monitoring,
                     'organization': organization,
                     'current_title': current_title,
                     'title': title,
                 },
                 template_name="task_list.html",)


@reversion.create_revision
@login_required
def task_add(request, monitoring_id, organization_id=None):
    monitoring = get_object_or_404(Monitoring, pk = monitoring_id)
    if organization_id:
        organization = get_object_or_404(Organization, pk = organization_id)
        redirect = '%s?%s' % (reverse('exmo2010:tasks_by_monitoring_and_organization', args=[monitoring.pk, organization.pk]), request.GET.urlencode())
        title = _('Add new task for %s') % organization.name
    else:
        organization = None
        redirect = '%s?%s' % (reverse('exmo2010:tasks_by_monitoring', args=[monitoring.pk]), request.GET.urlencode())
        title = _('Add new task for %s') % monitoring

    redirect = redirect.replace("%","%%")
    current_title = _('Add task')
    if request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        if request.method == 'GET':
            form = TaskForm(initial={'organization': organization}, monitoring=monitoring)

            crumbs = ['Home', 'Monitoring', 'Organization']
            breadcrumbs(request, crumbs, monitoring)

            return render_to_response(
                'exmo2010/task_form.html',
                {
                    'monitoring': monitoring,
                    'organization': organization,
                    'current_title': current_title,
                    'title': title,
                    'form': form
                },
                context_instance=RequestContext(request),
            )
        if request.method == 'POST':
            form = TaskForm(request.POST, monitoring=monitoring)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(redirect)
            else:

                crumbs = ['Home', 'Monitoring', 'Organization']
                breadcrumbs(request, crumbs, monitoring)

                return render_to_response(
                    'exmo2010/task_form.html',
                    {
                        'monitoring': monitoring,
                        'organization': organization,
                        'current_title': current_title,
                        'title': title,
                        'form': form
                    },
                    context_instance=RequestContext(request),
                )
    else:
        return HttpResponseForbidden(_('Forbidden'))


class TaskManagerView(SingleObjectTemplateResponseMixin, ModelFormMixin, ProcessFormView):
    model = Task
    context_object_name = "object"
    form_class = TaskForm
    template_name = "task_status.html"
    extra_context = {}

    def get_redirect(self, request, monitoring, organization, organization_id=None):
        organization_from_get = request.GET.get('organization', '')
        if organization_id or organization_from_get:
            q = request.GET.copy()
            if organization_from_get:
                q.pop('organization')
            redirect = '%s?%s' % (reverse('exmo2010:tasks_by_monitoring_and_organization',
                                  args=[monitoring.pk, organization.pk]), q.urlencode())
        else:
            redirect = '%s?%s' % (reverse('exmo2010:tasks_by_monitoring',
                                          args=[monitoring.pk]), request.GET.urlencode())
        redirect = redirect.replace("%", "%%")
        return redirect

    def get_context_data(self, **kwargs):
        context = super(TaskManagerView, self).get_context_data(**kwargs)
        context.update(self.extra_context)
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        organization = self.object.organization
        monitoring = organization.monitoring
        organization_id = self.kwargs.get('organization_id')
        self.success_url = self.get_redirect(request, monitoring, organization, organization_id)

        valid_methods = ['delete', 'approve', 'close',
                         'open', 'update', 'get', ]
        if self.kwargs["method"] not in valid_methods:
            HttpResponseForbidden(_('Forbidden'))

        current_title = title = _('Edit task')

        if self.kwargs["method"] == 'delete':
            title = _('Delete task %s') % self.object
            if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
                return HttpResponseForbidden(_('Forbidden'))
            else:
                self.template_name = "exmo2010/task_confirm_delete.html"
                crumbs = ['Home', 'Monitoring', 'Organization']
                breadcrumbs(request, crumbs, self.object)
                current_title = _('Delete task')
                self.extra_context = {'monitoring': monitoring,
                                      'organization': organization,
                                      'current_title': current_title,
                                      'title': title,
                                      'deleted_objects': Score.objects.filter(task=self.object), }

        if self.kwargs["method"] == 'close':
            title = _('Close task %s') % self.object
            if not request.user.has_perm('exmo2010.close_task', self.object):
                return HttpResponseForbidden(_('Forbidden'))
            else:
                if self.object.open:
                    try:
                        reversion.set_comment(_('Task ready'))
                        self.object.ready = True
                    except ValidationError, e:
                        return HttpResponse('%s' % e.message_dict.get('__all__')[0])
                else:
                    return HttpResponse(_('Already closed'))

        if self.kwargs["method"] == 'approve':
            title = _('Approve task for %s') % self.object
            if not request.user.has_perm('exmo2010.approve_task', self.object):
                return HttpResponseForbidden(_('Forbidden'))
            else:
                if not self.object.approved:
                    try:
                        reversion.set_comment(_('Task approved'))
                        self.object.approved = True
                    except ValidationError, e:
                        return HttpResponse('%s' % e.message_dict.get('__all__')[0])
                else:
                    return HttpResponse(_('Already approved'))
        if self.kwargs["method"] == 'open':
            title = _('Open task %s') % self.object
            if not request.user.has_perm('exmo2010.open_task', self.object):
                return HttpResponseForbidden(_('Forbidden'))
            else:
                if not self.object.open:
                    try:
                        reversion.set_comment(_('Task openned'))
                        self.object.open = True
                    except ValidationError, e:
                        return HttpResponse('%s' % e.message_dict.get('__all__')[0])
                else:
                    return HttpResponse(_('Already open'))
        if self.kwargs["method"] == 'update':
            title = _('Edit task %s') % self.object
            self.template_name = "exmo2010/task_form.html"
            if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
                return HttpResponseForbidden(_('Forbidden'))
            else:
                reversion.set_comment(_('Task updated'))
                crumbs = ['Home', 'Monitoring', 'Organization']
                breadcrumbs(request, crumbs, self.object)
                self.extra_context = {
                    'monitoring': monitoring,
                    'organization': organization,
                    'current_title': current_title,
                    'title': title,
                }

        self.extra_context['title'] = title
        self.extra_context['current_title'] = current_title

        return super(TaskManagerView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        organization = self.object.organization
        monitoring = organization.monitoring
        organization_id = self.kwargs.get('organization_id')
        self.success_url = self.get_redirect(request, monitoring, organization, organization_id)
        if self.kwargs["method"] == 'delete':
            self.object = self.get_object()
            self.object.delete()
            return HttpResponseRedirect(self.get_success_url())
        elif self.kwargs["method"] == 'update':
            return super(TaskManagerView, self).post(request, *args, **kwargs)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(TaskManagerView, self).dispatch(*args, **kwargs)


def task_history(request, task_id):

    task = Task.objects.get(pk=task_id)
    history = TaskHistory.objects.filter(task=task_id)

    crumbs = ['Home', 'Monitoring', 'Organization']
    breadcrumbs(request, crumbs, task)

    return render_to_response(
        'task_history.html',
        {
            'task': task,
            'history': history,
            'current_title': _('Organization'),
            'title': _('%s') % task.organization.name,
        },
        context_instance=RequestContext(request),
    )


def tasks_by_monitoring(request, monitorgin_id):
    monitoring = get_object_or_404(Monitoring, pk=monitorgin_id)
    profile = None
    if request.user.is_active:
        profile = request.user.profile
    if not request.user.has_perm('exmo2010.view_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    title = _('Task list for %(monitoring)s') % {'monitoring': monitoring}
    task_list = []
    queryset = Task.objects.filter(organization__monitoring=monitoring).\
    select_related()
    for task in queryset:
        if request.user.has_perm('exmo2010.view_task', task):
            task_list.append(task.pk)
    if not task_list and not \
    request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    queryset = Task.objects.filter(pk__in=task_list)
    if request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        users = User.objects.filter(task__organization__monitoring = monitoring).distinct()
        UserChoice = [(u.username, u.profile.legal_name) for u in users]
        headers = (
            (_('organization'), 'organization__name', 'organization__name',
             None, None),
            (_('expert'), 'user__username', 'user__username', None, UserChoice),
            (_('status'), 'status', 'status', int, Task.TASK_STATUS),
            (_('complete, %'), None, None, None, None),
            )
    elif profile and profile.is_expert:
        headers = (
            (_('organization'), 'organization__name', 'organization__name',
             None, None),
             (_('status'), 'status', 'status', int, Task.TASK_STATUS),
             (_('complete, %'), None, None, None, None),
            )
    else:
        headers = (
            (_('organization'), 'organization__name', 'organization__name',
             None, None),
            )

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs)

    if request.expert:
        current_title = _('Monitoring cycle')
    else:
        current_title = _('Rating') if monitoring.status == 5 else _('Tasks')

    return table(
        request,
        headers,
        queryset = queryset,
        paginate_by = 50,
        extra_context = {
            'monitoring': monitoring,
            'current_title': current_title,
            'title': title,
            'invcodeform': SettingsInvCodeForm(),
        },
        template_name="task_list.html",
    )


@login_required
def task_mass_assign_tasks(request, id):
    monitoring = get_object_or_404(Monitoring, pk = id)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        return HttpResponseForbidden(_('Forbidden'))
    organizations = Organization.objects.filter(monitoring = monitoring)
    title = _('Mass assign tasks')
    groups = []
    for group_name in ['expertsA','expertsB','expertsB_manager']:
        group, created = Group.objects.get_or_create(name = group_name)
        groups.append(group)
    users = User.objects.filter(is_active = True).filter(groups__in = groups)
    log = []
    if request.method == 'POST' and request.POST.has_key('organizations') and request.POST.has_key('users'):
        for organization_id in request.POST.getlist('organizations'):
            for user_id in request.POST.getlist('users'):
                try:
                    user = User.objects.get(pk = (user_id))
                    organization = Organization.objects.get(pk = int(organization_id))
                    task = Task(
                        user = user,
                        organization = organization,
                        status = Task.TASK_OPEN,
                    )
                    task.full_clean()
                    task.save()
                except ValidationError, e:
                    log.append('; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()]))
                except Exception, e:
                    log.append(e)
                else:
                    log.append('%s: %s' % (user.userprofile.legal_name, organization.name))

    crumbs = ['Home', 'Monitoring']
    breadcrumbs(request, crumbs)

    if request.expert:
        current_title = _('Monitoring cycle')
    else:
        current_title = _('Rating') if monitoring.status == 5 else _('Tasks')

    return render_to_response(
        'mass_assign_tasks.html', {
            'organizations': organizations,
            'users': users,
            'monitoring': monitoring,
            'log': log,
            'current_title': current_title,
            'title': title,
        }, context_instance=RequestContext(request))


def task_user_change_notify(sender, **kwargs):
    """
    Оповещение об измененях задачи.

    """
    task = sender
    email = task.user.email
    subject = _('You have an assigned task')
    headers = {
        'X-iifd-exmo': 'task_user_change_notification'
    }
    if Site._meta.installed:
        site = Site.objects.get_current()
        url = '%s://%s%s' % ('http', site, reverse('exmo2010:score_list_by_task', args=[task.pk]))
    else:
        url = None

    t = loader.get_template('task_user_changed.html')
    c = Context({'task': task, 'url': url, 'subject': subject})
    message = t.render(c)

    email = EmailMessage(subject, message, config_value('EmailServer', 'DEFAULT_FROM_EMAIL'), [email], headers=headers)
    email.encoding = "utf-8"
    email.content_subtype = "html"
    email.send()
