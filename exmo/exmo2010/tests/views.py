# -*- coding: utf-8 -*-
# This file is part of EXMO2010 software.
# Copyright 2010, 2011 Al Nikolov
# Copyright 2010, 2011, 2012 Institute for Information Freedom Development
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


# Канва для написания юнит-тестов для новых тикетов, при запуске тестов
# лучше перезаписывать настройки для основной базы данных (можно для всего
# этого дела создать пустой после синка и миграции sqlite-файл), так как для
# большой базы тестовая копия создается очень медленно. А тестовые данные
# заносить фикстурами или в коде тестов.


from django.test import TestCase

class GeneralViewsTests(TestCase):
    def test_index_page(self):
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, '/exmo2010/', status_code=301)
        self.assertContains(response, '<p>Copyright 2010, 2011 Al Nikolov</p>')



