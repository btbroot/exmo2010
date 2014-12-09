# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
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
from optparse import make_option

from django.core.management.commands.makemessages import Command as DjangoMakeMessages


class Command(DjangoMakeMessages):

    option_list = DjangoMakeMessages.option_list + (
        make_option('--origin', '-o', action='store_true', dest='origin',
                    default=False, help='Call origin Django makemessages function.'),
    )

    def handle_noargs(self, *args, **options):
        # Always remove obsolete message strings and do not break
        # long message lines into several lines if no 'origin' option.
        if not options.get('origin'):
            options['no_obsolete'] = True
            options['no_wrap'] = True
        super(Command, self).handle_noargs(*args, **options)
