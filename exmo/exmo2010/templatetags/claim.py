from django.template import Library, Node
from django.template import Variable, resolve_variable
from exmo2010.models import Claim

register = Library()

class ClaimByScore(Node):
    def __init__(self, score, varname):
        self.score, self.varname = score, varname

    def render(self, context):
        score = resolve_variable(self.score, context)
        context[self.varname] = Claim.objects.filter(score = score)
        return ''

def get_all_claim(parser, token):
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError, "get_all_claim tag takes exactly three arguments"
    if bits[2] != 'as':
        raise template.TemplateSyntaxError, "second argument to get_all_claim tag must be 'as'"
    return ClaimByScore(bits[1], bits[3])

get_all_claim = register.tag(get_all_claim)
