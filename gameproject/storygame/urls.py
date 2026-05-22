from django.urls import path
from . import views

urlpatterns = [
    path('', views.game, name='game'),
    path('scene/<int:scene_id>/', views.game, name='scene'),
]