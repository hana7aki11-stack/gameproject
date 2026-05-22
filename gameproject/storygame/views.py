from django.shortcuts import render, get_object_or_404
from .models import Scene


def game(request, scene_id=1):
    scene = get_object_or_404(
        Scene,
        id=scene_id
    )

    context = {
        'scene': scene
    }

    return render(
        request,
        'storygame/game.html',
        context
    )

