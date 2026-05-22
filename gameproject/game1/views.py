from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.http import JsonResponse

def index(request):
    return render(request, 'game1/index.html')

def save_score(request):
    data = json.loads(request.body)
    score = data["score"]

    print("スコア:", score)

    return JsonResponse({"status": "ok"})