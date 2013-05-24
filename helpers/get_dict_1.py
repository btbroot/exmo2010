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
Формирование файла files.py с временным словарем соответствий id-шников организаций ИРСИ и файлом sites.csv.

"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exmo.settings")

path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'exmo')
sys.path.append(path)

from core.utils import UnicodeReader
from exmo2010.models import Organization


monitorings = [50, 51, 48, 49]

f = open('files.py', 'w')
head = "# -*- coding: utf-8 -*-\n\ngosbook_id = {\n"
f.write(head.encode('UTF-8'))

orgs = Organization.objects.filter(monitoring__pk__in=monitorings)

for org in orgs:
    if org.url:
        flag = False
        url = "    #%s\n" % org.url
        f.write(url.encode('UTF-8'))
        org_id = "    %s: " % org.pk
        f.write(org_id.encode('UTF-8'))
        url = org.url.strip().replace('http://', '').replace('www.', '')
        if url[-1] == '/':
            url = url[:-1]

        for row in UnicodeReader(open('sites.csv', 'r'), encoding='UTF-8'):
            if row[0] and row[2]:
                url2 = row[2].strip().replace('http://', '').replace('www.', '')
                if url2[-1] == '/':
                    url2 = url2[:-1]

                if url == url2:
                    pk = "%s" % row[0]
                    f.write(pk.encode('UTF-8'))
                    flag = True
                    break

        if not flag:
            empty = '"None"'
            f.write(empty.encode('UTF-8'))
        br = ",\n"
        f.write(br.encode('UTF-8'))

tail = "}"
f.write(tail.encode('UTF-8'))
f.close()
