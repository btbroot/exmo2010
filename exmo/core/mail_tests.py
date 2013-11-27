# coding: utf-8
from django.core import mail
from django.test import SimpleTestCase
from django.utils.six import string_types


class HeadersCheckMixin(object):

    def assertMessageHasHeaders(self, message, headers):
        """
        Check that :param message: has all :param headers: headers.

        :param message: can be an instance of an email.Message subclass or a
        string with the contens of an email message.
        :param headers: should be a set of (header-name, header-value) tuples.
        """
        if isinstance(message, string_types):
            just_headers = message.split('\n\n', 1)[0]
            hlist = just_headers.split('\n')
            pairs = [hl.split(':', 1) for hl in hlist]
            msg_headers = {(n, v.lstrip()) for (n, v) in pairs}
        else:
            msg_headers = set(message.items())
        self.assertTrue(headers.issubset(msg_headers), msg='Message is missing '
                        'the following headers: %s' % (headers - msg_headers),)


class BaseEmailBackendTests(HeadersCheckMixin, object):
    email_backend = None

    def get_mailbox_content(self):
        raise NotImplementedError('subclasses of BaseEmailBackendTests must provide a get_mailbox_content() method')

    def get_the_message(self):
        mailbox = self.get_mailbox_content()
        self.assertEqual(len(mailbox), 1,
            "Expected exactly one message, got %d.\n%r" % (len(mailbox), [
                m.as_string() for m in mailbox]))
        return mailbox[0]


class LocmemBackendTests(BaseEmailBackendTests, SimpleTestCase):
    email_backend = 'django.core.mail.backends.locmem.EmailBackend'

    def get_mailbox_content(self):
        return [m.message() for m in mail.outbox]
