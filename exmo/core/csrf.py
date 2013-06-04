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
from django.conf import settings
from django.middleware.csrf import *
from django.utils.http import same_origin
from django.utils.crypto import constant_time_compare


def _sanitize_token(token):
    if len(token) > CSRF_KEY_LENGTH:
        return get_random_string(CSRF_KEY_LENGTH)
    token = re.sub('[^a-zA-Z0-9]+', '', str(token.decode('ascii', 'ignore')))
    if token == "":
        return get_random_string(CSRF_KEY_LENGTH)
    return token


class CsrfViewMiddlewareCustom(CsrfViewMiddleware):

    def process_view(self, request, callback, callback_args, callback_kwargs):

        if getattr(request, 'csrf_processing_done', False):
            return None

        try:
            csrf_token = _sanitize_token(
                request.COOKIES[settings.CSRF_COOKIE_NAME])
            request.META['CSRF_COOKIE'] = csrf_token
        except KeyError:
            csrf_token = None
            request.META["CSRF_COOKIE"] = get_random_string(CSRF_KEY_LENGTH)

        if getattr(callback, 'csrf_exempt', False):
            return None

        if request.method not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            if getattr(request, '_dont_enforce_csrf_checks', False):
                return self._accept(request)

            if request.is_secure():

                referer = request.META.get('HTTP_REFERER')
                if referer is None:
                    logger.warning('Forbidden (%s): %s',
                                   REASON_NO_REFERER, request.path,
                        extra={
                            'status_code': 403,
                            'request': request,
                        }
                    )
                    return self._reject(request, REASON_NO_REFERER)

                good_referer = 'https://%s/' % request.get_host()
                if not same_origin(referer, good_referer):
                    reason = REASON_BAD_REFERER % (referer, good_referer)
                    logger.warning('Forbidden (%s): %s', reason, request.path,
                        extra={
                            'status_code': 403,
                            'request': request,
                        }
                    )
                    return self._reject(request, reason)

            if csrf_token is None:
                logger.warning('Forbidden (%s): %s',
                               REASON_NO_CSRF_COOKIE, request.path,
                    extra={
                        'status_code': 403,
                        'request': request,
                    }
                )

                _send_email_about_cookies(request, REASON_NO_CSRF_COOKIE)

                return self._reject(request, REASON_NO_CSRF_COOKIE)

            request_csrf_token = ""
            if request.method == "POST":
                request_csrf_token = request.POST.get('csrfmiddlewaretoken', '')

            if request_csrf_token == "":
                request_csrf_token = request.META.get('HTTP_X_CSRFTOKEN', '')

            if not constant_time_compare(request_csrf_token, csrf_token):
                logger.warning('Forbidden (%s): %s',
                               REASON_BAD_TOKEN, request.path,
                    extra={
                        'status_code': 403,
                        'request': request,
                    }
                )
                return self._reject(request, REASON_BAD_TOKEN)

        return self._accept(request)


def _send_email_about_cookies(request, subj):

    from core.tasks import send_email

    req = []
    req.append('Method:  %s;' % request.method)
    req.append('GET:  %s;' % request.GET)
    req.append('POST:  %s;' % request.POST)
    req.append('COOKIES:  %s;' % request.COOKIES)
    req.append('META:')
    meta = '%s' % request.META
    req.extend(meta[1:-1].split(', '))
    try:
        send_email.delay(settings.COOKIES_ERROR_REPORT,
                         subj, 'cookies_fail',
                         context={'subject': subj, 'request': req})
    except:
        pass
