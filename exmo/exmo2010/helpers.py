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
#from contrib.admin
from django.utils.translation import ugettext_lazy, ugettext as _
from django.utils.text import capfirst, get_text_list
def construct_change_message(request, form, formsets):
        """
        Construct a change message from a changed object.
        """
        change_message = []
        if form.changed_data:
            change_message.append(_('Changed %s.') % get_text_list(form.changed_data, _('and')))

        if formsets:
            for formset in formsets:
                for added_object in formset.new_objects:
                    change_message.append(_('Added %(name)s "%(object)s".')
                                          % {'name': force_unicode(added_object._meta.verbose_name),
                                             'object': force_unicode(added_object)})
                for changed_object, changed_fields in formset.changed_objects:
                    change_message.append(_('Changed %(list)s for %(name)s "%(object)s".')
                                          % {'list': get_text_list(changed_fields, _('and')),
                                             'name': force_unicode(changed_object._meta.verbose_name),
                                             'object': force_unicode(changed_object)})
                for deleted_object in formset.deleted_objects:
                    change_message.append(_('Deleted %(name)s "%(object)s".')
                                          % {'name': force_unicode(deleted_object._meta.verbose_name),
                                             'object': force_unicode(deleted_object)})
        change_message = ' '.join(change_message)
        return change_message or _('No fields changed.')


PERM_NOPERM=0
PERM_ADMIN=1
PERM_EXPERT=2
PERM_ORGANIZATION=3
PERM_CUSTOMER=4

def check_permission(user, task):
    '''check user permission for task and scores of task'''
    groups = user.groups.all()
    if user.is_superuser:
        return PERM_ADMIN
    elif Group.objects.get(name='experts') in groups and user == task.user:
        return PERM_EXPERT
    elif Group.objects.get(name='customers') in groups and task.status == TASK_APPROVED:
        return PERM_CUSTOMER
    elif Group.objects.get(name='organizations') in groups and task.status == TASK_APPROVED:
        try:
            g = Group.objects.get(name = task.organization.keyname)
            if g in groups:
                return PERM_ORGANIZATION
        except:
            return PERM_NOPERM
    else:
        return PERM_NOPERM
