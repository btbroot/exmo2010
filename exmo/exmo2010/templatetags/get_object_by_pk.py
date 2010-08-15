from django.template import Library, Node
from django.db.models import get_model
from django.template import Variable, resolve_variable


register = Library()

class ObjectByPk(Node):
    def __init__(self, model, pk, varname):
        self.pk, self.varname = pk, varname
        self.model = get_model(*model.split('.'))

    def render(self, context):
        pk_id = resolve_variable(self.pk, context)
        context[self.varname] = self.model._default_manager.get(pk=pk_id)
        return ''

def get_object_by_pk(parser, token):
    bits = token.contents.split()
    if len(bits) != 5:
        raise TemplateSyntaxError, "get_object_by_pk tag takes exactly four arguments"
    if bits[3] != 'as':
        raise TemplateSyntaxError, "third argument to get_object_by_pk tag must be 'as'"
    return ObjectByPk(bits[1], bits[2], bits[4])

get_object_by_pk = register.tag(get_object_by_pk)
