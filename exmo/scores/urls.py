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
from django.conf.urls.defaults import *


urlpatterns = \
    patterns('scores.views',
             url(r'^(\d+)/$', 'score_view', name='score_view'),
             url(r'^(\d+)_(\d+)/$', 'score_add', name='score_add'),
             url(r'^(\d+)_(\w+)/$', 'score_manager', name='score_manager'),
             url(r'^(\d+)/claimstatus/$', 'score_claim_color', name='score_claim_color'),
             url(r'^(\d+)/comment/add/$', 'score_add_comment', name='score_add_comment'),
             url(r'^(\d+)/commentunreaded/$', 'score_comment_unreaded', name='score_commentunreaded'),
             )

urlpatterns += \
    patterns('claims.views',
             url(r'^(\d+)/claim/add$', 'claim_manager', name='claim_manager'),
             url(r'^(\d+)/claim/create/$', 'claim_create',  name='claim_create'),
             )

urlpatterns += \
    patterns('clarifications.views',
             url(r'^(\d+)/clarification/create/$', 'clarification_create', name='clarification_create'),
             )
