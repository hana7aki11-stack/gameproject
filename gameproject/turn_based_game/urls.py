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
    path('timing_game/', views.timing_game, name='timing_game'),
    path('count_game/', views.count_game, name='count_game'),

    # ミニゲームの途中中断
    path(
        'minigame-abandon/',
        views.abandon_minigame,
        name='minigame_abandon'
    ),

    # プレイ時間計測
    path(
        'play-heartbeat/',
        views.play_heartbeat,
        name='play_heartbeat'
    ),
    path(
        'end-play-session/',
        views.end_play_session,
        name='end_play_session'
    ),
]