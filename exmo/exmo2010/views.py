# Create your views here.
from exmo.exmo2010.models import Score
from django.shortcuts import render_to_response, get_object_or_404

def index(request):
  score_list = Score.objects.all()
  return render_to_response('exmo2010/index.html', {
    'score_list': score_list,
  })

def detail(request, score_id):
  s = get_object_or_404(Score, pk = score_id)
  return render_to_response('exmo2010/detail.html', {
    'score': s,
  })