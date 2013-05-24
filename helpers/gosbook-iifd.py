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
Вывод в консоль различий между списком организаций ИРСИ и файлом sites.csv (список организаций gosbook.ru).

"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exmo.settings")

path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'exmo')
sys.path.append(path)

from core.utils import UnicodeReader
from exmo2010.models import Organization
try:
    from results_old import gosbook_id
except:
    gosbook_id = {}


reader = UnicodeReader(open('sites.csv', 'r'), encoding='UTF-8')
result = []
res_dict = {}
res_dict.update(gosbook_id)
not_found = []
row_count = 0
monitorings = [50, 51, 48, 49]

for row in reader:
    row_count += 1
    found = False
    if row[0] and int(row[0]) in gosbook_id.values():
        continue

    if row[0] and row[2]:
        url = row[2].strip().replace('http://', '').replace('www.', '')
        if url[-1] == '/':
            url = url[:-1]
        o = Organization.objects.filter(monitoring__pk__in=monitorings, url__icontains=url)
        if o.exists() and o[0].pk not in res_dict:
            result.append("    #%s\n    %s: %s" % (url, o[0].pk, int(row[0])))
            res_dict[o[0].pk] = int(row[0])
            found = True
    elif row[0] and row[1]:
        name = row[1]
        o = Organization.objects.filter(monitoring__pk__in=monitorings, name__icontains=name)
        if o.exists() and o[0].pk not in res_dict:
            result.append("    #%s\n    %s: %s" % (name, o[0].pk, int(row[0])))
            res_dict[o[0].pk] = int(row[0])
            found = True
    if not found:
        not_found.append("    #%s\n    : %s" % (row[1], int(row[0])))

orgs = Organization.objects.filter(monitoring__pk__in=monitorings)
not_found_gosbook_id = []
for org in orgs:
    if org.pk in res_dict:
        continue
    else:
        not_found_gosbook_id.append(org)

sys.stdout.write("total org: %d\n" % Organization.objects.filter(monitoring__pk__in=monitorings).count())
sys.stdout.write("total in dict: %d\n" % len(res_dict))
sys.stdout.write("row count: %d\n" % row_count)
sys.stdout.write("not found: %d\n" % len(not_found))
sys.stdout.write("organization without gosbook id: %d\n" % len(not_found_gosbook_id))
for o in not_found_gosbook_id:
    sys.stdout.write("[%d] %s\n" % (o.pk, o.name))

print "# -*- coding: utf-8 -*-"
print "gosbook_id = {"
print ",\n".join(result)
print "}"

print "'''"
print "gosbook_id.update({"
print ",\n".join(not_found)
print "})"

print "'''"
