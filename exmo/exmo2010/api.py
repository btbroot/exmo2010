from django.utils import simplejson
from django.http import HttpResponse
from exmo.exmo2010.models import Organization
from django.db.models import Q


def organization_lookup(request):
    # Default return list
    results = []
    if request.method == "GET":
        if u'q' in request.GET:
            value = request.GET[u'q']
            # Ignore queries shorter than length 3
            if len(value) > 2:
                for word in value.split(" "):
                    model_results = Organization.objects.filter(
                                                            Q(name__icontains=word) |
                                                            Q(keywords__icontains=word) |
                                                            Q(url__icontains=word)
                                                         )
                results = [ x.name for x in model_results ]
    json = ""
    for x in results:
	json = "%s \n %s" % (x, json)
#    json = simplejson.dumps(results)
    return HttpResponse(json, mimetype='application/json')
