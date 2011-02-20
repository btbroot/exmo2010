from django.conf import settings
from django.contrib.auth.models import User
from exmo.exmo2010.helpers import check_permission

class ObjectPermBackend(object):
    supports_object_permissions = True
    supports_anonymous_user = True

    def authenticate(self, username, password):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if obj is None:
            return False
        return check_permission(user_obj, perm, obj)
