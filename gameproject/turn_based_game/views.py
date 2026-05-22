from django.shortcuts import render
import random
from datetime import datetime
from zoneinfo import ZoneInfo

def home(request):

    # 初回だけ初期値を作る
    if (
            'satisfaction' not in request.session
            or 'fullness' not in request.session
    ):
        request.session['satisfaction'] = 50
        request.session['energy'] = 50
        request.session['growth'] = 0
        request.session['fullness'] = 50
        request.session['turn'] = 1

    # セッションから現在値を取得
    satisfaction = request.session['satisfaction']
    energy = request.session['energy']
    growth = request.session['growth']
    fullness = request.session['fullness']
    turn = request.session['turn']

    # ボタン判定
    action = request.GET.get('action')
    event_message = ""

    # 毎回初期化
    show_food = False
    show_ball = False
    show_sleep = False
    last_action = None

    # ゲーム終了判定
    game_end = False

    if energy <= 0 or growth >= 50:
        game_end = True

    # ごはん
    if action == 'food' and not game_end:
        satisfaction += 10
        energy += 5
        fullness += 30
        growth += 2
        turn += 1

        # 一瞬だけ表示
        show_food = True

    elif action == 'play' and not game_end:
        satisfaction += 15
        energy -= 10
        growth += 3
        fullness -= 15
        turn += 1

        # ボール表示
        show_ball = True

    elif action == 'rest' and not game_end:
        satisfaction -= 5
        energy += 20
        fullness -= 5
        growth += 1
        turn += 1

        # Zzz表示
        show_sleep = True

    # リセット
    elif action == 'reset':
        satisfaction = 50
        energy = 50
        growth = 0
        fullness = 50
        turn = 1

    # イベントメッセージ
    event_message = ""

    # 3ターンごとのランダムイベント
    if turn % 3 == 0:

        event = random.randint(1, 4)

        # 楽しいことがあった
        if event == 1:
            satisfaction += 20
            event_message = "楽しいことがあった！満足度アップ！"

        # 疲れた
        elif event == 2:
            energy -= 15
            event_message = "疲れてしまった…元気ダウン"

        # 成長
        elif event == 3:
            growth += 5
            event_message = "大きく成長した！"

        # 何もない
        else:
            event_message = "特になにもなかった"

    # パラメータ上限・下限

    satisfaction = max(0, min(100, satisfaction))
    energy = max(0, min(100, energy))
    growth = max(0, min(50, growth))
    fullness = max(0, min(100, fullness))

    # 更新後の値を保存
    request.session['satisfaction'] = satisfaction
    request.session['energy'] = energy
    request.session['growth'] = growth
    request.session['fullness'] = fullness
    request.session['turn'] = turn


    # パラメータ依存イベント

    # 元気が低い
    if energy <= 20:
        growth -= 2
        event_message += " 疲れているみたい…成長度ダウン"

    # 満足度が高い
    if satisfaction >= 100:
        growth += 3
        event_message += " ごきげん！成長度アップ"

    # 満腹すぎる
    if fullness >= 80:
        satisfaction -= 5
        growth -= 2
        event_message += " お腹いっぱいで遊びたくない…"

    # 満腹なのにごはん
    if fullness >= 80 and action == 'food':
        satisfaction -= 10
        energy -= 5
        event_message += " お腹いっぱいで食べられない…"

    # 元気が低いのに遊ぶ
    if energy <= 20 and action == 'play':
        satisfaction -= 10
        growth -= 3
        event_message += " 疲れていて遊べないみたい…"

    # 絶好調
    if satisfaction >= 80 and energy >= 80:
        growth += 5
        event_message += " 絶好調！すごく元気！"

    # 弱っている状態
    if energy <= 20 and fullness <= 20:
        growth -= 2
        event_message += " 弱っているみたい…"


    # 成長度によって画像変更
    if growth < 20:
        character_image = 'images/character1.png'

    elif growth < 50:
        character_image = 'images/character2.png'

    else:
        character_image = 'images/character3.png'

    # 更新後のゲーム終了判定
    if energy <= 0 or growth >= 50:
        game_end = True

    # ゲーム状態
    game_status = ""

    # ゲームオーバー
    if energy <= 0:
        game_status = "つかれて眠ってしまった…ゲームオーバー"

    # エンディング
    elif growth >= 50:
        game_status = "大きく成長した！ゲームクリア！"

    # 日本時間を取得
    japan_time = datetime.now(ZoneInfo("Asia/Tokyo"))
    hour = japan_time.hour

    # 背景画像
    if 6 <= hour < 12:
        background_image = 'images/morning.png'

    elif 12 <= hour < 18:
        background_image = 'images/noon.png'

    else:
        background_image = 'images/night.png'


    status = {
        'satisfaction': satisfaction,
        'energy': energy,
        'growth': growth,
        'fullness': fullness,
        'turn': turn,
        'event_message': event_message,
        'character_image': character_image,
        'background_image': background_image,
        'game_status': game_status,
        'game_end': game_end,
        'last_action': last_action,
        'show_food': show_food,
        'show_ball': show_ball,
        'show_sleep': show_sleep,

    }

    return render(
        request,
        'turn_based_game/home.html',
        status
    )