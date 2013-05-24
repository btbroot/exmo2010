#!/usr/bin/python
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
"""
Формирование итогового словаря соответствий id-шников ИРСИ и gosbook.ru и запись в results.py.

"""
from files import gosbook_id as new_file
from results_old import gosbook_id as old_file


f = open('results.py', 'w')
head = "# -*- coding: utf-8 -*-\n\ngosbook_id = {\n"
f.write(head.encode('UTF-8'))

for k, v in old_file.items():
    if k in new_file.keys():
        new_file[k] = v

for k, v in new_file.items():
    body = "    %d: %s,\n" % (k, v)
    f.write(body.encode('UTF-8'))

tail = "}\n"
f.write(tail.encode('UTF-8'))
f.close()
