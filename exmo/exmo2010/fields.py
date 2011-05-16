"""
A custom Model Field for tagging.
"""
from tagging.fields import TagField as TagField_orig
from django.core import validators

class TagField(TagField_orig):
    """
    A "special" character field that actually works as a relationship to tags
    "under the hood". This exposes a space-separated string of tags, but does
    the splitting/reordering/etc. under the hood.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 255)
        kwargs['blank'] = kwargs.get('blank', True)
        super(TagField, self).__init__(*args, **kwargs)
        self.validators = [] #hack. but nothing to validate

    def get_internal_type(self):
        return 'TextField'
