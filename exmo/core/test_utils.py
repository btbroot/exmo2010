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
from contextlib import contextmanager

from django.conf import settings
from django.core import mail
from django.db import transaction
from django.test import LiveServerTestCase, SimpleTestCase, Client
from django.test.client import RequestFactory
from django.test.testcases import disable_transaction_methods, restore_transaction_methods
from django.utils import translation
from django.utils.decorators import method_decorator
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException

try:
    from pyvirtualdisplay import Display
except ImportError:
    pass
else:
    if getattr(settings, 'SELENIUM_XVFB_ENABLED', False):
        # Run all selenium tests in xvfb (browser window will be invisible)
        display = Display(visible=0, size=(800, 600))
        display.start()


TIMEOUT = getattr(settings, 'SELENIUM_TEST_TIMEOUT', 6)


def _find(self, selector):
    try:
        return self.find_element_by_css_selector(selector)
    except Exception:
        return None


def _findall(self, selector):
    return self.find_elements_by_css_selector(selector)


# Monkey-patch selenium WebElement to have convenient find and findall methods to search children.
WebElement.find = _find
WebElement.findall = _findall


class BaseSeleniumTestCase(LiveServerTestCase):
    """
    Base class for all selenium tests
    To configure default webdriver used, set SELENIUM_WEBDRIVER in your settings.py
    possible values: FALLBACK PhantomJS Firefox Chrome Opera
    default: FALLBACK - will try to find first working webdriver

    """

    @classmethod
    def setUpClass(cls):
        if not getattr(cls, '__unittest_skip__', False):
            webdriver_type = getattr(settings, 'SELENIUM_WEBDRIVER', 'FALLBACK')
            if webdriver_type == 'FALLBACK':
                for webdriver_type in 'Firefox PhantomJS Chrome Opera'.split():
                    try:
                        cls.webdrv = getattr(webdriver, webdriver_type)()
                    except Exception:
                        continue
                    break
                else:
                    raise Exception("Can't find any webdriver. Make sure that it is installed and in $PATH")
            else:
                cls.webdrv = getattr(webdriver, webdriver_type)()
        translation.activate(settings.LANGUAGE_CODE)

        super(BaseSeleniumTestCase, cls).setUpClass()
        cls.requestfactory = RequestFactory(SERVER_NAME=cls.server_thread.host, SERVER_PORT=cls.server_thread.port)

    @classmethod
    def tearDownClass(cls):
        translation.deactivate()
        if not getattr(cls, '__unittest_skip__', False):
            cls.webdrv.quit()
        super(BaseSeleniumTestCase, cls).tearDownClass()

    def find(self, selector):
        try:
            return self.webdrv.find_element_by_css_selector(selector)
        except Exception:
            return None

    def findall(self, selector):
        return self.webdrv.find_elements_by_css_selector(selector)

    def _assertWebElementMethod(self, selector, method, expected_result, wait_timeout=TIMEOUT):
        def condition(*args):
            elements = self.findall(selector)
            if elements:
                return all(item == expected_result for item in map(method, elements))
        WebDriverWait(self.webdrv, wait_timeout).until(condition)

    def assertVisible(self, selector, wait_timeout=TIMEOUT):
        try:
            self._assertWebElementMethod(selector, WebElement.is_displayed, True, wait_timeout)
        except TimeoutException:
            raise AssertionError('Element is missing or not visible: %s' % selector)

    def assertHidden(self, selector, wait_timeout=TIMEOUT):
        try:
            self._assertWebElementMethod(selector, WebElement.is_displayed, False, wait_timeout)
        except TimeoutException:
            raise AssertionError('Element is missing or not hidden: %s' % selector)

    def assertEnabled(self, selector, wait_timeout=TIMEOUT):
        try:
            self._assertWebElementMethod(selector, WebElement.is_enabled, True, wait_timeout)
        except TimeoutException:
            raise AssertionError('Element is missing or not enabled: %s' % selector)

    def assertDisabled(self, selector, wait_timeout=TIMEOUT):
        try:
            self._assertWebElementMethod(selector, WebElement.is_enabled, False, wait_timeout)
        except TimeoutException:
            raise AssertionError('Element is missing or not disabled: %s' % selector)

    def get(self, url):
        self.webdrv.get(self.live_server_url + str(url))

    def login(self, username, password):
        self.get(settings.LOGIN_URL)
        self.find("#id_email").send_keys(username)
        self.find('#id_password').send_keys(password)
        self.find('input[type=submit]').click()
        self.assertEqual(self.webdrv.current_url, self.live_server_url + str(settings.LOGIN_REDIRECT_URL))

    @method_decorator(contextmanager)
    def frame(self, iframe_selector):
        """
        Contextmanager to switch webdriver inside iframe and back
        Usage:
        >>> with self.frame('iframe'):
        ...    # manipulate DOM inside iframe
        ...    self.find('#element_inside_iframe')
        ...
        """
        self.webdrv.switch_to.frame(self.find(iframe_selector))
        yield
        self.webdrv.switch_to.default_content()


class OptimizedTestCase(SimpleTestCase):
    """
    This testcase will not reset database between tests, so database setup may be done once in setUpClass method.
    Database will be reset only in tearDownClass (with transaction rollback).
    As with django TestCase - transactions does not work within the test itself, they are monekeypatched
    to do nothing.
    """

    @classmethod
    def setUpClass(cls):
        super(OptimizedTestCase, cls).setUpClass()
        transaction.enter_transaction_management(using='default')
        transaction.managed(True, using='default')
        disable_transaction_methods()
        cls.client = Client()

        # Flush mail outbox after previous testcases.
        mail.outbox = []

    @classmethod
    def tearDownClass(cls):
        super(OptimizedTestCase, cls).tearDownClass()
        restore_transaction_methods()
        transaction.rollback(using='default')
        transaction.leave_transaction_management(using='default')
