# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Foundation "Institute for Information Freedom Development"
# Copyright 2013 Al Nikolov
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


def change_organization_status(sender, **kwargs):
    """
    Check all organizations with 'registered' invitation status for activity.

    """
    comment = kwargs['comment']
    organization = comment.content_object.task.organization
    user_profile = comment.user.profile
    if organization.inv_status == 'RGS' and organization in user_profile.organization.all():
        organization.inv_status = 'ACT'
        organization.save()
