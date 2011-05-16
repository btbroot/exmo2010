"""
A custom Model Field for tagging.
"""
from tagging.fields import TagField

class TagField(TagField):
    """
    A "special" character field that actually works as a relationship to tags
    "under the hood". This exposes a space-separated string of tags, but does
    the splitting/reordering/etc. under the hood.
    """
    def __init__(self, *args, **kwargs):
        kwargs['blank'] = kwargs.get('blank', True)
        if kwargs.has_key('create_synonyms'):
            self.create_synonyms = kwargs.pop('create_synonyms')
        else:
            self.create_synonyms = None
        super(TagField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'TextField'
