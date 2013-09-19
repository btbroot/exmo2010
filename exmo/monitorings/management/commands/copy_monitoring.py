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
from copy import deepcopy
from optparse import make_option

from django.contrib.comments.models import Comment
from django.core.management.base import BaseCommand, CommandError

from exmo2010.models import *


class Command(BaseCommand):
    """Copy monitoring.
    USAGE without comments:
        python manage.py monitoring_pk
    USAGE with comments:
        python manage.py monitoring_pk --comments

    """
    args = '<monitoring_pk monitoring_pk ... >'

    option_list = BaseCommand.option_list + (
        make_option('--comments',
                    action='store_true',
                    dest='comments',
                    default=False,
                    help='Copy with comments'),
    )

    def handle(self, *args, **options):
        with_comments = options.get('comments')
        for monitoring_pk in args:
            try:
                monitoring = Monitoring.objects.get(pk=monitoring_pk)
            except Monitoring.DoesNotExist:
                raise CommandError('Monitoring "%s" does not exist!' % monitoring_pk)

            copied_monitoring = deepcopy(monitoring)
            copied_monitoring.pk = None
            copied_monitoring.name = '%s_copy' % monitoring.name
            copied_monitoring.status = MONITORING_RATE
            copied_monitoring.save()
            self.stdout.write('Monitoring ID - %d' % copied_monitoring.pk)

            organization_map = {}
            parameter_map = {}

            tasks = Task.objects.filter(organization__monitoring=monitoring)
            for count, task in enumerate(tasks):
                if (count+1) % 5 == 0:
                    self.stdout.write('%d(%d)' % (count+1, len(tasks)))
                org = deepcopy(task.organization)
                org.pk = None
                org.monitoring = copied_monitoring
                org.inv_code = generate_inv_code(6)
                try:
                    org.save()
                except Exception:
                    org = Organization.objects.get(name=org.name, monitoring=copied_monitoring)
                organization_map[task.organization.pk] = org.pk
                copied_task = deepcopy(task)
                copied_task.pk = None
                copied_task.organization = org
                copied_task.save()
                scores = Score.objects.filter(task=task)
                for score in scores:
                    if Parameter.objects.filter(monitoring=copied_monitoring, code=score.parameter.code).exists():
                        param = Parameter.objects.get(monitoring=copied_monitoring, code=score.parameter.code)
                    else:
                        param = deepcopy(score.parameter)
                        param.pk = None
                        param.monitoring = copied_monitoring
                        param.save()
                        param.exclude.clear()
                        parameter_map[score.parameter.pk] = param.pk
                    copied_score = deepcopy(score)
                    copied_score.pk = None
                    copied_score.task = copied_task
                    copied_score.parameter = param
                    copied_score.save()

                    if with_comments:
                        comments = Comment.objects.for_model(Score).filter(object_pk=score.pk)
                        for comment in comments:
                            copied_comment = deepcopy(comment)
                            copied_comment.pk = None
                            copied_comment.object_pk = copied_score.pk
                            copied_comment.save()

            for param_pk, new_param_pk in parameter_map.iteritems():
                param = Parameter.objects.get(pk=param_pk)
                new_param = Parameter.objects.get(pk=new_param_pk)
                for org_pk in param.exclude.values_list('pk', flat=True):
                    if org_pk in organization_map:
                        new_param.exclude.add(Organization.objects.get(pk=organization_map[org_pk]))

            self.stdout.write('Successfully copied monitoring "%s".' % monitoring_pk)
