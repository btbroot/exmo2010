#http://code.djangoproject.com/ticket/8399
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

import inspect



def disable_for_loaddata(signal_handler):
    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        for fr in inspect.stack():
            if inspect.getmodulename(fr[1]) in  ('loaddata','syncdb'):
                return
        signal_handler(*args, **kwargs)
    return wrapper
