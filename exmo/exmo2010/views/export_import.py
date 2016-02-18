# -*- coding: utf-8 -*-
# Copyright 2016 IRSI LTD
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
import os
import tempfile
import zipfile
from collections import OrderedDict
from copy import deepcopy
from cStringIO import StringIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.urlresolvers import reverse
from django.db import connection
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_protect
from django.utils import simplejson
from django.utils.translation import ugettext as _
from reversion.revisions import default_revision_manager as revision

from exmo2010.models import (LicenseTextFragments, Monitoring, Organization,
                             Parameter, Score, Task, generate_inv_code)
from core.utils import UnicodeReader, UnicodeWriter, dictfetchall
from core.views import login_required_on_deny


def replace_string(cell):
    cell = cell.replace(';', ',')
    cell = cell.replace(', ', ',')
    cell = cell.replace(',\n', ',')
    cell = cell.replace(',\t', ',')
    cell = cell.replace('\t', ',')
    tmp = []
    for item in cell.split(','):
        tmp.append(item.strip())
    cell = ', '.join(tmp)
    return cell


class MonitoringExport(object):
    def __init__(self, monitoring):
        self.monitoring = monitoring
        cursor = connection.cursor()
        cursor.execute(monitoring.sql_scores())
        scores = dictfetchall(cursor)
        cursor.close()

        if not len(scores):
            return

        if monitoring.openness_expression.code == 1:
            criteria = Parameter.OPTIONAL_CRITERIA_V1
        else:
            criteria = Parameter.OPTIONAL_CRITERIA

        # dict with organization as keys and el as list of scores for json export
        self.tasks = OrderedDict()
        rating_place = 0
        current_openness = None

        for score in scores:
            # skip score from non-approved task
            if score['task_status'] != Task.TASK_APPROVED:
                continue

            if not current_openness or score['task_openness'] != current_openness:
                rating_place += 1
                current_openness = score['task_openness']

            score_dict = {
                'name': score['parameter_name'].strip(),
                'social': score['weight'],
                'found': score['found'],
                'type': 'npa' if score['parameter_npa'] else 'other',
                'revision': Score.REVISION_EXPORT[score['revision']],
                'id': score['parameter_id'],
                'links': (score['links'] or '').strip(),
                'recommendations': (score['recommendations'] or '').strip(),
            }
            if settings.DEBUG:
                score_dict['pk'] = score['id']

            for criterion in criteria:
                if score[criterion] != -1:
                    score_dict[criterion] = float(score[criterion])

            if score['organization_id'] in self.tasks.keys():
                self.tasks[score['organization_id']]['scores'].append(score_dict)
            else:
                if score['task_openness'] is not None:
                    score['task_openness'] = '%.3f' % score['task_openness']
                if score['openness_initial'] is not None:
                    score['openness_initial'] = '%.3f' % score['openness_initial']

                self.tasks[score['organization_id']] = {
                    'scores': [score_dict, ],
                    'position': rating_place,
                    'openness': score['task_openness'],
                    'openness_initial': score['openness_initial'],
                    'name': score['organization_name'],
                    'id': score['organization_id'],
                    'url': score['url'],
                }

    def json(self):
        ret = {
            'monitoring': {
                'name': self.monitoring.name,
                'tasks': self.tasks.values(),
            },
        }
        license = LicenseTextFragments.objects.filter(pk='license')
        json_license = license[0].json_license if license else {}
        if json_license:
            ret.update({'license': json_license})
        json_dump_args = {}
        if settings.DEBUG:
            json_dump_args = {'indent': 2}
        response = HttpResponse(mimetype='application/json')
        response.encoding = 'UTF-8'
        response['Content-Disposition'] = 'attachment; filename=monitoring-%s.json' % self.monitoring.pk
        response.write(
            simplejson.dumps(
                ret, **json_dump_args
            ).decode("unicode_escape").encode("utf8"))
        return response

    def csv(self):
        response = HttpResponse(mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = \
            'attachment; filename=monitoring-%s.csv' % self.monitoring.pk
        response.encoding = 'UTF-16'
        writer = UnicodeWriter(response)
        # csv HEAD
        writer.writerow([
            "#Monitoring",
            "Organization",
            "Organization_id",
            "Position",
            "Initial Openness",
            "Openness",
            "Parameter",
            "Parameter_id",
            "Found",
            "Complete",
            "Topical",
            "Accessible",
            "Hypertext",
            "Document",
            "Image",
            "Social",
            "Type",
            "Revision",
            "Links",
            "Recommendations"
        ])

        score_fields = ['name', 'id', 'found'] + Parameter.OPTIONAL_CRITERIA
        score_fields += ['social', 'type', 'revision', 'links', 'recommendations']
        for task in self.tasks.values():
            for score_dict in task['scores']:
                row = [
                    self.monitoring.name,
                    task['name'],
                    task['id'],
                    task['position'],
                    task['openness_initial'],
                    task['openness'],
                ]
                row.extend([unicode(score_dict.get(c, "not relevant")) for c in score_fields])
                writer.writerow(row)
        # csv FOOTER
        license = LicenseTextFragments.objects.filter(pk='license')
        if license:
            writer.writerow([u'#%s' % license[0].csv_footer])

        return response


@login_required_on_deny
def monitoring_export(request, monitoring_pk):
    """
    :param request:
        django request object with GET var 'format'
        export format could be 'json' or 'csv'
    :param monitoring_pk:
        monitoring pk
    :return:
        json or csv with all scores for monitoring
    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.view_monitoring', monitoring):
        raise PermissionDenied

    export_format = request.GET.get('format', 'json')
    if export_format == 'csv':
        return MonitoringExport(monitoring).csv()
    elif export_format == 'json':
        return MonitoringExport(monitoring).json()
    raise PermissionDenied


@login_required
def monitoring_parameter_export(request, monitoring_pk):
    """
    Экспорт параметров в CSV
    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        raise PermissionDenied

    parameters = Parameter.objects.filter(monitoring=monitoring)
    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=monitoring-parameters-%s.csv' % monitoring_pk
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)
    writer.writerow([
        '#Code',
        'Name',
        'Grounds',
        'Rating procedure',
        'Notes',
        'Complete',
        'Topical',
        'Accessible',
        'Hypertext',
        'Document',
        'Image',
        'Weight',
    ])
    for p in parameters:
        out = (
            p.code,
            p.name,
            p.grounds,
            p.rating_procedure,
            p.notes,
            int(p.complete),
            int(p.topical),
            int(p.accessible),
            int(p.hypertext),
            int(p.document),
            int(p.image),
            p.weight
        )
        writer.writerow(out)
    license = LicenseTextFragments.objects.filter(pk='license')
    if license:
        writer.writerow([u'#%s' % license[0].csv_footer])

    return response


@login_required
def monitoring_organization_export(request, monitoring_pk):
    """
    Экспорт организаций в CSV.

    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        raise PermissionDenied

    organizations = Organization.objects.filter(monitoring=monitoring)
    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=monitoring-organization-%s.csv' % monitoring_pk
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)
    writer.writerow([
        '#Name',
        'Url',
        'Email',
        'Phone',
        'recommendations_hidden',
        'Code',
        'Invitation link',
    ])
    for o in organizations:
        out = (
            o.name,
            o.url,
            o.email,
            o.phone,
            str(o.recommendations_hidden),
            o.inv_code,
            request.build_absolute_uri(reverse('exmo2010:auth_orguser') + '?code={}'.format(o.inv_code)),
        )
        writer.writerow(out)
    license = LicenseTextFragments.objects.filter(pk='license')
    if license:
        writer.writerow([u'#%s' % license[0].csv_footer])

    return response


@login_required
@csrf_protect
def monitoring_organization_import(request, monitoring_pk):
    """
    Импорт организаций из CSV.

    """
    must_register = False
    if revision.is_registered(Organization):
        revision.unregister(Organization)
        must_register = True

    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        raise PermissionDenied
    if 'orgfile' not in request.FILES:
        return HttpResponseRedirect(reverse('exmo2010:monitorings_list'))
    reader = UnicodeReader(request.FILES['orgfile'])
    errors = []
    indexes = {}
    rowOKCount = 0
    row_num = 0
    try:
        for row_num, row in enumerate(reader, start=1):
            if row[0] and row[0].startswith('#'):
                for key in ['name', 'url', 'email', 'phone', 'recommendations_hidden']:
                    for item in row:
                        if item and key in item.lower():
                            indexes[key] = row.index(item)
                errors.append("row %d. Starts with '#'. Skipped" % row_num)
                continue

            if 'name' not in indexes:
                errors.append("header row (csv). Field 'Name' does not exist")
                break

            if row[indexes['name']] == '':
                errors.append("row %d (csv). Empty organization name" % row_num)
                continue
            try:
                organization = Organization.objects.get(monitoring=monitoring, name=row[indexes['name']])
            except Organization.DoesNotExist:
                organization = Organization(name=row[indexes['name']])
                organization.monitoring = monitoring
            except Exception, e:
                errors.append("row %d. %s" % (row_num, e))
                continue
            try:
                if row[indexes['email']]:
                    organization.email = replace_string(row[indexes['email']]).strip()
                if row[indexes['phone']]:
                    organization.phone = replace_string(row[indexes['phone']]).strip()
                if row[indexes['url']]:
                    organization.url = row[indexes['url']].strip()
                if row[indexes['recommendations_hidden']] == 'False':
                    organization.recommendations_hidden = False
                if row[indexes['recommendations_hidden']] == 'True':
                    organization.recommendations_hidden = True

                organization.inv_code = generate_inv_code(6)
                organization.full_clean()
                organization.save()
            except ValidationError, e:
                errors.append("row %d (validation). %s" % (
                    row_num,
                    '; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()])))
            except Exception, e:
                errors.append("row %d. %s" % (row_num, e))
            else:
                rowOKCount += 1
    except csv.Error, e:
        errors.append(_("row %(row)d (csv). %(raw)s") % {'row': row_num, 'raw': e})
    except UnicodeError:
        errors.append(_("File, you are loading is not valid CSV."))
    except Exception, e:
        errors.append(_("Import error: %s." % e))

    if must_register:
        revision.register(Organization)

    return TemplateResponse(request, 'exmo2010/csv_import_log.html', {
        'monitoring': monitoring,
        'errors': errors,
        'row_count': '{}/{}'.format(rowOKCount, row_num),
    })


@login_required
@csrf_protect
def monitoring_parameter_import(request, monitoring_pk):
    """
    Импорт параметров из CSV.

    """
    must_register = False
    if revision.is_registered(Parameter):
        revision.unregister(Parameter)
        must_register = True

    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.edit_monitoring', monitoring):
        raise PermissionDenied
    if 'paramfile' not in request.FILES:
        return HttpResponseRedirect(reverse('exmo2010:monitorings_list'))
    reader = UnicodeReader(request.FILES['paramfile'])
    errors = []
    rowOKCount = 0
    row_num = 0
    try:
        for row_num, row in enumerate(reader, start=1):
            if row[0].startswith('#'):
                errors.append("row %d. Starts with '#'. Skipped" % row_num)
                continue
            if row[0] == '':
                errors.append("row %d (csv). Empty code" % row_num)
                continue
            if row[1] == '':
                errors.append("row %d (csv). Empty name" % row_num)
                continue
            try:
                code = row[0]
                name = row[1]
                parameter = Parameter.objects.get(monitoring=monitoring, code=code, name=name)
            except Parameter.DoesNotExist:
                parameter = Parameter()
            except Exception, e:
                errors.append("row %d. %s" % (row_num, e))
                continue
            try:
                parameter.monitoring = monitoring
                parameter.code = code
                parameter.name = name
                # Присваиваем пустую строку, а не None.
                parameter.grounds = row[2] or ''
                parameter.rating_procedure = row[3] or ''
                parameter.notes = row[4] or ''
                parameter.complete = bool(int(row[5]))
                parameter.topical = bool(int(row[6]))
                parameter.accessible = bool(int(row[7]))
                parameter.hypertext = bool(int(row[8]))
                parameter.document = bool(int(row[9]))
                parameter.image = bool(int(row[10]))
                parameter.weight = row[11]
                parameter.full_clean()
                parameter.save()
            except ValidationError, e:
                errors.append("row %d (validation). %s" % (
                    row_num,
                    '; '.join(['%s: %s' % (i[0], ', '.join(i[1])) for i in e.message_dict.items()])))
            except Exception, e:
                errors.append("row %d. %s" % (row_num, e))
            else:
                rowOKCount += 1
    except csv.Error, e:
        errors.append(_("row %(row)d (csv). %(raw)s") % {'row': row_num, 'raw': e})
    except UnicodeError:
        errors.append(_("File, you are loading is not valid CSV."))
    except Exception, e:
        errors.append(_("Import error: %s." % e))

    if must_register:
        revision.register(Parameter)

    return TemplateResponse(request, 'exmo2010/csv_import_log.html', {
        'monitoring': monitoring,
        'errors': errors,
        'row_count': '{}/{}'.format(rowOKCount, row_num),
    })


@login_required
def monitoring_by_criteria_mass_export(request, monitoring_pk):
    """
    Экспорт по критерию
    Архив из CVS файлов -- по файлу на критерий.

    """
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied

    row_template = {
        'Found': [],
        'Complete': [],
        'Topical': [],
        'Accessible': [],
        'Hypertext': [],
        'Document': [],
        'Image': []
    }
    spool = {}
    writer = {}
    handle = {}
    for criteria in row_template.keys():
        spool[criteria] = tempfile.mkstemp()
        handle[criteria] = os.fdopen(spool[criteria][0], 'w')
        writer[criteria] = UnicodeWriter(handle[criteria])
    header_row = True
    parameters = Parameter.objects.filter(monitoring=monitoring)
    for task in Task.approved_tasks.filter(organization__monitoring=monitoring):
        row = deepcopy(row_template)
        if header_row:
            for criteria in row.keys():
                row[criteria] = [''] + [p.code for p in parameters]
                writer[criteria].writerow(row[criteria])
            header_row = False
            row = deepcopy(row_template)
        for criteria in row.keys():
            row[criteria] = [task.organization.name]
        for parameter in parameters:
            try:
                score = Score.objects.filter(task=task, parameter=parameter, revision=Score.REVISION_DEFAULT)[0]
                if task.organization in parameter.exclude.all():
                    raise IndexError
            except IndexError:
                row['Found'].append('')
                row['Complete'].append('')
                row['Topical'].append('')
                row['Accessible'].append('')
                row['Hypertext'].append('')
                row['Document'].append('')
                row['Image'].append('')
            else:
                row['Found'].append(score.found)
                if score.parameter.complete:
                    row['Complete'].append(score.complete)
                else:
                    row['Complete'].append('')
                if score.parameter.topical:
                    row['Topical'].append(score.topical)
                else:
                    row['Topical'].append('')
                if score.parameter.accessible:
                    row['Accessible'].append(score.accessible)
                else:
                    row['Accessible'].append('')
                if score.parameter.hypertext:
                    row['Hypertext'].append(score.hypertext)
                else:
                    row['Hypertext'].append('')
                if score.parameter.document:
                    row['Document'].append(score.document)
                else:
                    row['Document'].append('')
                if score.parameter.image:
                    row['Image'].append(score.image)
                else:
                    row['Image'].append('')
        for criteria in row.keys():
            writer[criteria].writerow(row[criteria])

    for criteria in row_template.keys():
        license = LicenseTextFragments.objects.filter(pk='license')
        if license:
            writer[criteria].writerow([u'#%s' % license[0].csv_footer])

    response = HttpResponse(mimetype='application/zip')
    response['Content-Disposition'] = 'attachment; filename=monitoring-%s.zip' % monitoring_pk
    buffer = StringIO()
    writer = zipfile.ZipFile(buffer, 'w')
    for criteria in row_template.keys():
        handle[criteria].close()
        writer.write(spool[criteria][1], criteria + '.csv')
        os.unlink(spool[criteria][1])
    writer.close()
    buffer.flush()
    response.write(buffer.getvalue())
    buffer.close()
    return response


@login_required
def representatives_export(request, monitoring_pk):
    monitoring = get_object_or_404(Monitoring, pk=monitoring_pk)
    if not request.user.has_perm('exmo2010.admin_monitoring', monitoring):
        raise PermissionDenied

    orgs = monitoring.organization_set.order_by('name')

    for org in orgs:
        org.users = []
        for user in sorted(org.userprofile_set.all(), key=lambda m: m.full_name):
            scores = Score.objects.filter(task__organization=org).values_list('pk', flat=True)
            user.comments = user.user.comment_comments.filter(object_pk__in=scores)
            org.users.append(user)

    response = HttpResponse(mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=representatives-%s.csv' % monitoring_pk
    response.encoding = 'UTF-16'
    writer = UnicodeWriter(response)
    writer.writerow([
        '#Verified',
        'Organization',
        'First name',
        'Last name',
        'Email',
        'Phone',
        'Job title',
        'Comments count',
        'Date joined',
        'Last login',
    ])

    for org in orgs:
        for user in org.users:
            row = [
                int(user.user.is_active),
                org.name,
                user.user.first_name,
                user.user.last_name,
                user.user.email,
                user.phone,
                user.position,
                user.comments.count(),
                user.user.date_joined.date().isoformat(),
                user.user.last_login.date().isoformat(),
            ]
            writer.writerow(row)

    license = LicenseTextFragments.objects.filter(pk='license')
    if license:
        writer.writerow([u'#%s' % license[0].csv_footer])

    return response
