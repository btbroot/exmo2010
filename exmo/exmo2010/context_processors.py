# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2013 Al Nikolov
# Copyright 2013-2014 Foundation "Institute for Information Freedom Development"
# Copyright 2014 IRSI LTD
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
from django.conf import settings
from livesettings import config_value

from . import models


def exmo2010(request):
    license = models.LicenseTextFragments.objects.filter(pk='license')
    context = {
        'models': models,
        'settings': settings,
        'livesettings': {
            'link_to_methodology': config_value('Links', 'LINK_TO_METHODOLOGY'),
            'og_description': config_value('GlobalParameters', 'OG:DESCRIPTION')
        },
        'fragments': {
            'license': license[0].page_footer if license else ''
        }
    }
    return {'exmo2010': context}
