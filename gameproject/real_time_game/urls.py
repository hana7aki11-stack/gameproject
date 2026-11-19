
from django.urls import path
from . import views


app_name = "real_time_game"


urlpatterns = [

    path(
        "",
        views.home,
        name="home"
    ),

    path(
        "start-test-game/",
        views.start_test_game,
        name="start_test_game"
    ),

    # イントロの終了
    path(
        "finish-intro/",
        views.finish_intro,
        name="finish_intro"
    ),

    path("skip-tutorial/", views.skip_tutorial, name="skip_tutorial"),
    # リアルタイム型の追加説明終了
    path(
        "finish-extra-intro/",
        views.finish_extra_intro,
        name="finish_extra_intro"
    ),

    # 新しい育成の開始
    path(
        "new-round/",
        views.new_round,
        name="new_round"
    ),

    # ゲームのリセット
    path(
        "reset/",
        views.reset_game,
        name="reset_game"
    ),

    # ログアウト
    path(
        "logout/",
        views.logout_game,
        name="logout_game"
    ),

    # 就寝時刻の変更
    path(
        "set-bedtime/",
        views.set_bedtime,
        name="set_bedtime"
    ),

    # シッターに預ける
    path(
        "deposit-sitter/",
        views.deposit_sitter,
        name="deposit_sitter"
    ),

    # シッターからお迎え
    path(
        "pickup-sitter/",
        views.pickup_sitter,
        name="pickup_sitter"
    ),

    # 家具・壁紙の操作
    path(
        "manage-item/",
        views.manage_item,
        name="manage_item"
    ),

    # 休む
    path(
        "rest/",
        views.rest,
        name="rest"
    ),

    # ボールキャッチ
    path(
        "ball-game/",
        views.ball_game,
        name="ball_game"
    ),

    # 好きなごはん選び
    path(
        "food-game/",
        views.food_game,
        name="food_game"
    ),

    # 火加減チャレンジ
    path(
        "timing-game/",
        views.timing_game,
        name="timing_game"
    ),

    # 食材かぞえ
    path(
        "count-game/",
        views.count_game,
        name="count_game"
    ),

    # 障害物よけ
    path(
        "dodge-game/",
        views.dodge_game,
        name="dodge_game"
    ),

    # ダンスまね
    path(
        "dance-game/",
        views.dance_game,
        name="dance_game"
    ),

    # ミニゲーム終了
    path(
        "finish-minigame/",
        views.minigame_result,
        name="finish_minigame"
    ),

    # ミニゲーム中断
    path(
        "abandon-minigame/",
        views.minigame_abandon,
        name="abandon_minigame"
    ),

    # プレイ時間の定期記録
    path(
        "play-heartbeat/",
        views.play_heartbeat,
        name="play_heartbeat"
    ),

    # プレイ終了の記録
    path(
        "end-play-session/",
        views.end_play_session,
        name="end_play_session"
    ),

]
