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
from reversion import revision

from core.utils import disable_for_loaddata
from exmo2010.models import Monitoring, Task


@disable_for_loaddata
def post_save_model(sender, instance, created, **kwargs):
    """
    Функция для тригера post-save-model
    Сейчас нужна лишь для сохранения openness_first.

    """
    must_register = False
    if revision.is_registered(instance.__class__):
        revision.unregister(instance.__class__)
        must_register = True
    #update task openness hook
    if instance.__class__ == Monitoring:
        for task in Task.objects.filter(organization__monitoring=instance):
            task.update_openness()
    if must_register:
        revision.register(instance.__class__)
