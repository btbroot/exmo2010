# This file is part of EXMO2010 software.
# Copyright 2010 Al Nikolov
# Copyright 2010 Institute for Information Freedom Development
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
from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from exmo.exmo2010.models import Score, Claim
from exmo.exmo2010.models import Monitoring
from exmo.exmo2010.forms import ClaimForm
from exmo.exmo2010.forms import ClaimReportForm
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.template import RequestContext
from django.core.urlresolvers import reverse
import exmo.exmo2010.views as exmo_views
from exmo.exmo2010 import signals
from django.contrib.auth.models import User
from datetime import datetime, timedelta

@csrf_protect
@login_required
def claim_manager(request, score_id, claim_id=None, method=None):
    if not request.user.is_superuser: return HttpResponseForbidden(_('Forbidden'))
    score = get_object_or_404(Score, pk = score_id)
    redirect = reverse(exmo_views.score_list_by_task, args=[score.task.pk])
    title = _('Add new claim for %s') % score
    if claim_id:
        claim = get_object_or_404(Claim, pk = claim_id)
    elif not method: #create new
        if request.method == 'GET':
            form = ClaimForm()
            form.fields['creator'].initial = request.user.pk
            form.fields['score'].initial = score.pk
            if not score.task.open:
                form.fields['open_task'].initial = True
        elif request.method == 'POST':
            form = ClaimForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['score'] == score and form.cleaned_data['creator'] == request.user:
                    claim = score.add_claim(request.user, form.cleaned_data['comment'])
                    if form.cleaned_data['open_task']:
                        score.task.open = True
                    signals.claim_was_posted.send(
                        sender  = Claim.__class__,
                        claim = claim,
                        request = request
                    )
                    return HttpResponseRedirect(redirect)
        return render_to_response(
            'exmo2010/claim_form.html',
            {
                'monitoring': score.task.monitoring,
                'task': score.task,
                'score': score,
                'title': title,
                'form': form,
            },
            context_instance=RequestContext(request),
        )



@csrf_protect
@login_required
def claim_report(request, monitoring_id):
    monitoring = get_object_or_404(Monitoring, pk = monitoring_id)
    title = _('Claims report for %(monitoring)s') % { 'monitoring': monitoring }
    claims = None
    if request.method == 'GET':
        form = ClaimReportForm()
        form.fields['from_date'].initial = datetime.now() - timedelta(days=30)
        form.fields['to_date'].initial = datetime.now()
    elif request.method == 'POST':
        form = ClaimReportForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['expert']
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']
            title = title + _(' for expert %s') % user
            if not request.user.is_superuser and user != request.user: return HttpResponseForbidden('Forbidden')
            claims = Claim.objects.filter(score__task__monitoring = monitoring, score__task__user = user, open_date__gte = from_date, open_date__lte = to_date)
    if request.user.is_superuser:
        form.fields['expert'].queryset = User.objects.filter(task__score__claim__isnull = False).annotate()
    else:
        form.fields['expert'].queryset = User.objects.filter(pk = request.user.pk)
    return render_to_response(
            'exmo2010/claim_report.html',
            {
                'monitoring': monitoring,
                'title': title,
                'form': form,
                'media': form.media,
                'claims': claims,
            },
            context_instance=RequestContext(request),
     )
