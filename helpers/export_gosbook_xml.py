#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011, 2013 Al Nikolov
# Copyright 2010, 2011 non-profit partnership Institute of Information Freedom Development
# Copyright 2012-2014 Foundation "Institute for Information Freedom Development"
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
Формирование XML-файла для gosbook.ru.

"""
import os
import sys
import time

from lxml import etree

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exmo.settings")

path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'exmo')
sys.path.append(path)

from exmo2010.models import Score, Parameter, Task
from results import gosbook_id


timestamp = str(int(time.time()))
FILENAME = "monitoring-%s.xml" % timestamp

monitorings_dict = {
    'foiv': [48, 50],
    'vroiv': [51],
    'moa': [49]
}


def get_rating(monitorings):
    tasks = Task.approved_tasks.filter(
        organization__monitoring__pk__in=monitorings,
        organization__pk__in=gosbook_id.keys(),
    )

    tasks = sorted(tasks, key=lambda task: task.openness, reverse=True)

    place = 1
    max_rating = tasks[0].openness
    rating_list = []
    for task in tasks:
        if task.openness < max_rating:
            place += 1
            max_rating = task.openness
        rating_list.append((place, task))
    return rating_list


def generate_xml_for_monitoring(tasks):
    sites = []

    for place, task in tasks:
        site = etree.Element("site", id=str(gosbook_id[task.organization.pk]))
        etree.SubElement(site, "rating").text = str(task.openness)
        etree.SubElement(site, "url").text = etree.CDATA(task.organization.url)
        etree.SubElement(site, "name").text = etree.CDATA(task.organization.name)
        etree.SubElement(site, "place").text = str(place)
        etree.SubElement(site, "edited").text = timestamp
        parameters = Parameter.objects.exclude(exclude=task.organization).filter(monitoring=task.organization.monitoring)
        scores = Score.objects.filter(task=task, parameter__in=parameters)
        questions = etree.Element("questions")
        for score in scores:
            question = etree.Element("question", id=str(score.parameter.pk))
            etree.SubElement(question, "text").text = etree.CDATA(score.parameter.name)
            etree.SubElement(question, "code").text = str(score.parameter.code)
            if score.edited:
                edited = str(int(time.mktime(score.edited.timetuple())))
            else:
                edited = timestamp
            etree.SubElement(question, "edited").text = edited

            etree.SubElement(question, "value").text = str(score.parameter.weight)
            etree.SubElement(question, "description").text = etree.CDATA(score.parameter.description)
            etree.SubElement(question, "found").text = str(score.found)
            if score.comment:
                scomment = score.comment
            else:
                scomment = ""
            etree.SubElement(question, "comment").text = etree.CDATA(scomment)

            # default values
            complete = topical = accessible = hypertext = document = image = 4

            #complete
            if score.parameter.complete and score.complete:
                complete = score.complete
            etree.SubElement(question, "complete").text = str(complete)

            #topical
            if score.parameter.topical and score.topical:
                topical = score.topical
            etree.SubElement(question, "topical").text = str(topical)

            #accessible
            if score.parameter.accessible and score.accessible:
                accessible = score.accessible
            etree.SubElement(question, "accessible").text = str(accessible)

            #hypertext
            if score.parameter.hypertext and score.hypertext:
                hypertext = score.hypertext
            etree.SubElement(question, "hypertext").text = str(hypertext)

            #document
            if score.parameter.document and score.document:
                document = score.document
            etree.SubElement(question, "document").text = str(document)

            #image
            if score.parameter.image and score.image:
                image = score.image
            etree.SubElement(question, "image").text = str(image)

            questions.append(question)
        site.append(questions)
        sites.append(site)
    return sites


def generate_xml():
    root = etree.Element("root")
    sites = etree.Element("sites")
    for name, monitorings in monitorings_dict.items():
        print name
        for site in generate_xml_for_monitoring(get_rating(monitorings)):
            sites.append(site)
    root.append(sites)
    handle = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)
    applic = open(FILENAME, "w")
    applic.writelines(handle)
    applic.close()

# def send_xml():
#     # with pycurl:
#     import pycurl
#     fields = [
#         ('xml', (pycurl.FORM_FILE, FILENAME)),
#     ]
#
#     c = pycurl.Curl()
#     c.setopt(c.URL, 'http://gosmonitor.ru:8080/integration/get_xml')
#     c.setopt(c.HTTPPOST, fields)
#     c.setopt(c.VERBOSE, 1)
#     c.perform()
#     c.close()
#
#     # or with urllib2:
#     import urllib2
#     req = urllib2.Request(url='http://gosmonitor.ru:8080/integration/get_xml',
#                           data=xml_string,  # add xml-string
#                           headers={'Content-Type': 'application/xml'}
#                           )
#     urllib2.urlopen(req)


if __name__ == "__main__":
    generate_xml()
    # send_xml()
