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
from datetime import date

from django.conf import settings
from django.utils.http import int_to_base36, base36_to_int
from django.utils.crypto import constant_time_compare, salted_hmac
from django.utils import six


class BaseTokenGenerator(object):
    """
    Base object used to generate and check tokens.
    Written based on django.contrib.auth.tokens
    """
    def make_token(self, user):
        """
        Returns a token for the given user.
        """
        # timestamp is number of days since 2001-1-1.  Converted to
        # base 36, this gives us a 3 digit string until about 2121
        timestamp = self.timestamp_today()
        timestamp_b36 = int_to_base36(timestamp)

        hash = self._make_hash(user, timestamp)
        return "%s-%s" % (timestamp_b36, hash)

    def check_token(self, user, token):
        """
        Check that token is correct for a given user.
        """
        try:
            timestamp_b36, hash = token.split("-")
            timestamp = base36_to_int(timestamp_b36)
        except ValueError:
            return False

        # Check that the timestamp/uid has not been tampered with
        if not constant_time_compare(self._make_hash(user, timestamp), hash):
            return False

        if (self.timestamp_today() - timestamp) > self.timeout_days:
            return False

        return True

    def _make_hash(self, user, timestamp):
        """
        Implement the hashing in subclass.
        """
        raise NotImplementedError

    def timestamp_today(self):
        return (date.today() - date(2001, 1, 1)).days


class PasswordResetTokenGenerator(BaseTokenGenerator):
    key_salt = "exmo2010.PasswordResetTokenGenerator"
    timeout_days = settings.PASSWORD_RESET_TIMEOUT_DAYS

    def _make_hash(self, user, timestamp):
        # By hashing on the internal state of the user and using state
        # that is sure to change (the password salt will change as soon as
        # the password is set, at least for current Django auth, and
        # last_login will also change), we produce a hash that will be
        # invalid as soon as it is used.

        # Ensure results are consistent across DB backends
        login_timestamp = user.last_login.replace(microsecond=0, tzinfo=None)

        userdata = six.text_type(user.pk) + user.password + six.text_type(login_timestamp)
        return salted_hmac(self.key_salt, userdata + six.text_type(timestamp)).hexdigest()[::2]


class EmailConfirmTokenGenerator(BaseTokenGenerator):
    key_salt = "exmo2010.EmailConfirmTokenGenerator"
    timeout_days = settings.EMAIL_CONFIRM_TIMEOUT_DAYS

    def _make_hash(self, user, timestamp):
        # Ensure results are consistent across DB backends
        login_timestamp = user.last_login.replace(microsecond=0, tzinfo=None)

        userdata = six.text_type(user.pk) + six.text_type(login_timestamp)
        return salted_hmac(self.key_salt, userdata + six.text_type(timestamp)).hexdigest()[::2]
