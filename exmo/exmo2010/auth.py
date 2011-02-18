from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from objperms.models import ObjectPermission

class ObjectPermBackend(object):
    supports_object_permissions = True
    supports_anonymous_user = True

    def authenticate(self, username, password):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated():
            user_obj = User.objects.get(pk=settings.ANONYMOUS_USER_ID)

        if obj is None:
            return False

        ct = ContentType.objects.get_for_model(obj)

        try:
            perm = perm.split('.')[-1].split('_')[0]
        except IndexError:
            return False

        p = ObjectPermission.objects.filter(content_type=ct,
                                            object_id=obj.id,
                                            user=user_obj)
        return p.filter(**{'can_%s' % perm: True}).exists()
