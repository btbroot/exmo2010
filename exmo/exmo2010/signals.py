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
"""
Signals relating to claims.
"""
from django.dispatch import Signal

# Sent just after a claim was posted. See above for how this differs
# from the claim object's post-save signal.
claim_was_posted_or_deleted = Signal(providing_args=["claim", "request", "creation"])
clarification_was_posted = Signal(providing_args=["clarification", "request"])
score_was_changed = Signal(providing_args=["form", "request"])
task_user_changed = Signal()


def org_changed(sender, instance, action, **kwargs):
    """
    Change organization`s invitation status if current user is the first member of this organization.

    """
    if action == 'post_add':
        for org in instance.organization.all():
            if org.userprofile_set.count():
                org.inv_status = 'RGS'
                org.save()
