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
from exmo.exmo2010.forms import ClaimForm
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.template import RequestContext
from django.core.urlresolvers import reverse
import exmo.exmo2010.views as exmo_views

@csrf_protect
@login_required
def claim_manager(request, score_id, claim_id=None, method=None):
    if not request.user.is_superuser: return HttpResponseForbidden(_('Forbidden'))
    score = get_object_or_404(Score, pk = score_id)
    redirect = reverse(exmo_views.score_detail_direct, args=[score.pk, 'update'])
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
        elif request.method == 'POST':
            form = ClaimForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['score'] == score and form.cleaned_data['creator'] == request.user:
                    form.save()
                    if form.cleaned_data['open_task']:
                        score.task.open = True
                    return HttpResponseRedirect(redirect)
                else:
                    return HttpResponse(_('form not valid'))
            else:
                return HttpResponse(_('form not valid'))
