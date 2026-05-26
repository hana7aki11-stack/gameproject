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
    reaction_state = "normal"

    # 最後の行動
    last_action = action

    # ゲーム終了判定
    game_end = False

    if energy <= 0 or growth >= 50:
        game_end = True

    # ごはん
    if action == 'food' and not game_end:

        # 空腹 → 大喜び
        if fullness <= 20:
            satisfaction += 20
            energy += 10
            fullness += 30
            growth += 4

            reaction_state = "happy_food"

        # 満腹 → 嫌がる
        elif fullness >= 80:
            satisfaction -= 10
            energy -= 5

            reaction_state = "reject_food"

        # 普通
        else:
            satisfaction += 10
            energy += 5
            fullness += 30
            growth += 2

            reaction_state = "normal_food"

        turn += 1




    elif action == 'play' and not game_end:

        # 元気 → 大喜び

        if energy >= 70:

            satisfaction += 20

            energy -= 10

            growth += 5

            fullness -= 15

            reaction_state = "happy_play"


        # 疲れ → 嫌がる

        elif energy <= 20:

            satisfaction -= 10

            growth -= 2

            reaction_state = "tired_play"


        # 普通

        else:

            satisfaction += 15

            energy -= 10

            growth += 3

            fullness -= 15

            reaction_state = "normal_play"

        turn += 1




    elif action == 'rest' and not game_end:

        # 疲れている → 気持ちいい

        if energy <= 20:

            energy += 30

            satisfaction += 10

            reaction_state = "good_rest"


        else:

            satisfaction -= 5

            energy += 20

            fullness -= 5

            growth += 1

            reaction_state = "normal_rest"

        turn += 1



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

    # -------------------------
    # キャラクター状態判定
    # -------------------------

    # 初期値
    character_state = "normal"

    # 疲れ優先
    if energy <= 20:
        character_state = "tired"

    # 空腹
    elif fullness <= 20:
        character_state = "hungry"

    # 満腹
    elif fullness >= 80:
        character_state = "full"

    # ごきげん
    elif satisfaction >= 80 or energy >= 80:
        character_state = "happy"

    # -------------------------
    # 成長段階 × 状態画像
    # -------------------------

    if growth < 20:

        if character_state == "happy":
            character_image = 'images/character1-happy.png'

        elif character_state == "tired":
            character_image = 'images/character1-tired.png'

        elif character_state == "hungry":
            character_image = 'images/character1-hungry.png'

        elif character_state == "full":
            character_image = 'images/character1-full.png'

        else:
            character_image = 'images/character1.png'


    elif growth < 50:

        if character_state == "happy":
            character_image = 'images/character2-happy.png'

        elif character_state == "tired":
            character_image = 'images/character2-tired.png'

        elif character_state == "hungry":
            character_image = 'images/character2-hungry.png'

        elif character_state == "full":
            character_image = 'images/character2-full.png'

        else:
            character_image = 'images/character2.png'


    else:

        character_image = 'images/character3.png'

    # -------------------------
    # 状態ごとの動き
    # -------------------------

    if character_state == "happy":
        character_animation = "happyBounce 0.8s ease-in-out infinite"

    elif character_state == "tired":
        character_animation = "tiredMove 3s ease-in-out infinite"

    elif character_state == "hungry":
        character_animation = "hungryShake 0.3s linear infinite"

    elif character_state == "full":
        character_animation = "fullMove 4s ease-in-out infinite"

    else:
        character_animation = "floatCharacter 2s ease-in-out infinite"


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

    # -------------------------
    # 感情アイコン
    # -------------------------
    show_heart = False
    show_sweat = False
    show_good = False
    show_food_icon = False

    # 満足高
    if satisfaction >= 80:
        show_heart = True

    # 疲れ
    if energy <= 20:
        show_sweat = True

    # 空腹
    if fullness <= 20:
        show_food_icon = True

    # 絶好調
    if satisfaction >= 80 and energy >= 80:
        show_good = True

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
        # 感情アイコン
        'show_heart': show_heart,
        'show_sweat': show_sweat,
        'show_good': show_good,
        'show_food_icon': show_food_icon,
        'character_animation': character_animation,
        'reaction_state': reaction_state,
    }

    return render(
        request,
        'turn_based_game/home.html',
        status
    )