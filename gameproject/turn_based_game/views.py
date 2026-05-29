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
        request.session['character_state'] = 'normal'

    # セッションから現在値を取得
    satisfaction = request.session['satisfaction']
    energy = request.session['energy']
    growth = request.session['growth']
    fullness = request.session['fullness']
    turn = request.session['turn']

    before_energy = energy
    before_fullness = fullness
    before_satisfaction = satisfaction

    # ボタン判定
    action = request.GET.get('action')
    event_message = ""
    reaction_state = "normal"
    menu = request.GET.get('menu', '')

    # 行動後はメニューを閉じる
    if action in [
        'salad', 'snack', 'meal',
        'ball', 'toy', 'bike',
        'rest'
    ]:
        menu = ''

    # 最後の行動
    last_action = action

    food_image = ""

    # 更新後のゲーム終了判定
    game_end = False

    if energy <= 0 or growth >= 100:
        game_end = True

    # -------------------------
    # ごはん系
    # -------------------------

    # サラダ
    if action == 'salad' and not game_end:

        satisfaction += 10
        energy += 8
        fullness += 10
        growth += 0

        reaction_state = "normal_food"
        turn += 1


    # おやつ
    elif action == 'snack' and not game_end:

        satisfaction += 25
        energy -= 5
        fullness += 8
        growth += 0

        reaction_state = "happy_food"
        turn += 1


    # 肉
    elif action == 'meal' and not game_end:

        satisfaction += 5
        energy += 15
        fullness += 30
        growth += 2

        reaction_state = "normal_food"
        turn += 1

    # -------------------------
    # あそぶ系
    # -------------------------

    if action == 'ball' and not game_end:

        satisfaction += 25
        energy -= 20
        fullness -= 15
        growth += 0

        reaction_state = "happy_play"
        turn += 1


    elif action == 'toy' and not game_end:

        satisfaction += 10
        energy -= 5
        fullness -= 5
        growth += 2

        reaction_state = "normal_play"
        turn += 1


    elif action == 'bike' and not game_end:

        satisfaction += 8
        energy += 12
        fullness -= 15
        growth += 1

        reaction_state = "normal_play"
        turn += 1


    # -------------------------
    # 休む
    # -------------------------

    elif action == 'rest' and not game_end:

        if energy <= 20:

            energy += 30
            satisfaction += 10

            reaction_state = "good_rest"

        else:

            satisfaction -= 5
            energy += 20
            fullness -= 5

            reaction_state = "normal_rest"

        turn += 1



    # リセット
    if action == 'reset':
        satisfaction = 50
        energy = 50
        growth = 0
        fullness = 50
        turn = 1
        character_state = "normal"

        request.session['character_state'] = 'normal'

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
            growth += 2
            event_message = "大きく成長した！"

        # 何もない
        else:
            event_message = "特になにもなかった"



    # -------------------------
    # パラメータ依存イベント
    # -------------------------

    # 初回アクセスだけnormal
    if action is None and menu == '':
        character_state = "normal"

    # ごはん・あそぶを押しただけなら前回維持
    else:
        character_state = request.session.get(
            'character_state',
            'normal'
        )

    # 実際に行動した時だけ判定する
    action_list = [
        'salad', 'snack', 'meal',
        'ball', 'toy', 'bike',
        'rest'
    ]

    if action in action_list:

        # 行動時だけnormalに戻して再判定
        character_state = "normal"

        # 元気が低い
        if energy <= 30:
            growth -= 2
            event_message += " 疲れているみたい…成長度ダウン"
            character_state = "tired"

        # 満足度が高い
        if satisfaction >= 80:
            growth += 1
            event_message += " ごきげん！成長度アップ"
            character_state = "happy"

        # 満腹すぎる
        if fullness >= 70:
            satisfaction -= 5
            growth -= 2
            event_message += " お腹いっぱいで遊びたくない…"
            character_state = "tired"

        # 満腹なのにごはん
        if (
                fullness >= 70
                and action in ['salad', 'snack', 'meal']
        ):
            satisfaction -= 10
            energy -= 5
            event_message += " お腹いっぱいなのに食べすぎた…"
            character_state = "tired"

        # 元気なのに休む
        if energy >= 90 and action == 'rest':
            satisfaction -= 15
            growth -= 2
            event_message += " まだ元気なのに寝ちゃった…"
            character_state = "tired"

        # 疲れているのに遊ぶ
        if (
                energy <= 30
                and action in ['ball', 'toy', 'bike']
        ):
            energy -= 10
            satisfaction -= 5
            event_message += " 疲れているのに遊んでしまった…"
            character_state = "tired"

        # 空腹なのに遊ぶ
        if (
                fullness <= 30
                and action in ['ball', 'toy', 'bike']
        ):
            satisfaction -= 10
            event_message += " お腹が空いて遊べない…"
            character_state = "tired"

        # 絶好調
        if satisfaction >= 80 and energy >= 80:
            growth += 2
            event_message += " 絶好調！すごく元気！"
            character_state = "happy"

        # 弱っている状態
        if energy <= 20 and fullness <= 20:
            growth -= 2
            event_message += " 弱っているみたい…"
            character_state = "tired"

    # 最終値を制限
    satisfaction = max(0, min(100, satisfaction))
    energy = max(0, min(100, energy))
    growth = max(0, min(100, growth))
    fullness = max(0, min(100, fullness))

    # セッション保存
    request.session['satisfaction'] = satisfaction
    request.session['energy'] = energy
    request.session['growth'] = growth
    request.session['fullness'] = fullness
    request.session['turn'] = turn
    request.session['event_message'] = event_message
    request.session['character_state'] = character_state

    print("energy", energy)
    print("fullness", fullness)
    print("satisfaction", satisfaction)


    # -------------------------
    # 成長段階 × 状態画像
    # -------------------------

    if growth < 40:

        if character_state == "happy":
            character_image = 'images/character1-happy.png'

        elif character_state == "tired":
            character_image = 'images/character1-tired.png'

        else:
            character_image = 'images/character1.png'


    elif growth < 100:

        if character_state == "happy":
            character_image = 'images/character2-happy.png'

        elif character_state == "tired":
            character_image = 'images/character2-tired.png'

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


    # ゲーム状態
    game_status = ""

    # ゲームオーバー
    if energy <= 0:
        game_status = "つかれて眠ってしまった…ゲームオーバー"

    # エンディング
    elif growth >= 100:
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
        'character_animation': character_animation,
        'reaction_state': reaction_state,
        'character_state': character_state,
        "food_image": food_image,
        'menu': menu,

    }

    return render(
        request,
        'turn_based_game/home.html',
        status
    )

def debug_view(request):

    status = {
        'satisfaction':
            request.session.get(
                'satisfaction', 0
            ),

        'energy':
            request.session.get(
                'energy', 0
            ),

        'growth':
            request.session.get(
                'growth', 0
            ),

        'fullness':
            request.session.get(
                'fullness', 0
            ),

        'turn':
            request.session.get(
                'turn', 0
            ),
    }

    return render(
        request,
        'turn_based_game/debug.html',
        status
    )
