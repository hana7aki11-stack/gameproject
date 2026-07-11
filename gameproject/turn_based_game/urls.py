from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('debug/', views.debug_view, name='debug'),
    path('signup/', views.signup, name='signup'),
    path('ball_game/', views.ball_game, name='ball_game'),
    path('food_game/', views.food_game, name='food_game'),
    path('dodge_game/', views.dodge_game, name='dodge_game'),
    path('dance_game/', views.dance_game, name='dance_game'),
    path('timing_game/', views.timing_game, name='timing_game'),  # 追加
    path('count_game/', views.count_game, name='count_game'),     # 追加
]