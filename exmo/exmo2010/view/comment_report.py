# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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
from exmo2010.view.helpers import table
from exmo2010.view.helpers import rating
from django.shortcuts import get_object_or_404, render_to_response
from django.views.generic.list_detail import object_list, object_detail
from django.views.generic.create_update import update_object, create_object
from django.views.generic.create_update import delete_object
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from exmo2010.models import Organization, Parameter, Score, Task
from exmo2010.models import Monitoring, Claim
from exmo2010.models import MonitoringStatus
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.contrib.comments import Comment
from django.db.models import Q
from django.db.models import Count
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.template import RequestContext
from django.views.decorators.cache import cache_page
from django.core.urlresolvers import reverse
from exmo2010.forms import MonitoringForm, MonitoringStatusForm, CORE_MEDIA
from reversion import revision
from exmo2010.utils import UnicodeReader, UnicodeWriter
import csv
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import auth


def get_comments_name(comment_type):
    """Convert from comment_type flag to string for read"""
    comments_name = ''
    if (comment_type == 'all_comments'):
        comments_name = 'All comments'
    if (comment_type == 'unrequited_comments'):
        comments_name = 'Unrequited comments'
    if (comment_type == 'respond_comments'):
        comments_name = 'Respond comments'
    if (comment_type == 'claim_comments'):
        comments_name = 'Claim comments'
    return comments_name


@login_required
@csrf_protect
def comment_report(request, offset, comment_type):
    """View for comment report
       Input parametrs:
       offset - page number
       comment_type - type of comment
    """
    try:
        offset = int(offset)
    except ValueError:
        raise Http404()

    pos_inc = offset
    pos_dec = offset
    offset -= 1
    offset *= 20
    pos_dec -= 1
    pos_inc += 1

    if not (request.user.profile.is_expert or request.user.is_superuser):
        return HttpResponseForbidden(_('Forbidden'))

    respond_comments = 0

    un = auth.get_user(request)

    ctitle = 'Comments'
    title = get_comments_name(comment_type)

    user_id = User.objects.get(username=un).id

    respond_count = 0
    unreq_count = 0

    comments = []
    if (comment_type == 'all_comments'):
        comments = Comment.objects.filter(user=user_id).\
                     order_by('-submit_date')[offset:offset + 20]
    if (comment_type == 'unrequited_comments'):
        #Use for future procedures#
        comments = []
    if (comment_type == 'respond_comments'):
        #Use for future procedures#
        comments = []
    if (comment_type == 'claim_comments'):
        #Use for future procedures#
        comments = []

    if (len(comments) < 20):
        next_stop = 1
    else:
        next_stop = 0

    return render_to_response('exmo2010/comment_report.html', {
        'comments': comments,
        'respond_comments': respond_comments,
        'respond_count': respond_count,
        'unrequited_count': unreq_count,
        'comment_type': comment_type,
        'pos_inc': pos_inc,
        'pos_dec': pos_dec,
        'next_stop': next_stop,
        'ctitle': ctitle,
        'title': title,
        'media': CORE_MEDIA,
        }, context_instance=RequestContext(request))
