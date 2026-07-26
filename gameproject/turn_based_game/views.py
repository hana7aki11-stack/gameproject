from django.shortcuts import render, redirect
import random
from datetime import datetime, timedelta
from urllib.parse import urlencode
from .models import SaveData
from django.contrib.auth import login
from .forms import SignUpForm
from django.urls import reverse


item_categories = {
    'plant': 'plant',
    'plant-star': 'plant',
    'plant-kawaii': 'plant',
    'sofa': 'sofa',
    'sofa-star': 'sofa',
    'sofa-kawaii': 'sofa',
    'rug': 'rug',
    'rug-star': 'rug',
    'rug-kawaii': 'rug',
    'clock': 'clock',
    'clock-star': 'clock',
    'clock-kawaii': 'clock',
}


def get_difficulty_list(growth_stage):
    DIFFICULTY_LEVELS = [
        {'key': 'easy',   'label': 'かんたん',   'required_stage': 0},
        {'key': 'normal', 'label': 'ふつう',     'required_stage': 1},
        {'key': 'hard',   'label': 'むずかしい', 'required_stage': 2},
        {'key': 'oni',    'label': 'おに',       'required_stage': 3},
    ]
    return [
        {
            'key': level['key'],
            'label': level['label'],
            'unlocked': growth_stage >= level['required_stage'],
        }
        for level in DIFFICULTY_LEVELS
    ]


def home(request):

    event_message = ""
    reaction_state = "normal"

    # -------------------------
    # セーブデータ自動ロード
    # -------------------------

    if request.user.is_authenticated and not request.session.get('auto_loaded', False):
        try:
            save_data = SaveData.objects.get(user=request.user)
            request.session['satisfaction'] = save_data.satisfaction
            request.session['energy'] = save_data.energy
            request.session['growth'] = save_data.growth
            request.session['fullness'] = save_data.fullness
            request.session['turn'] = save_data.turn
            request.session['remaining_time'] = save_data.remaining_time
            request.session['play_count'] = save_data.play_count
            request.session['healthy_food_count'] = save_data.healthy_food_count
            request.session['snack_count'] = save_data.snack_count
            request.session['character_state'] = save_data.character_state
            request.session['room_wallpaper'] = save_data.room_wallpaper
            request.session['items'] = save_data.items
            request.session['placed_items'] = save_data.placed_items
        except SaveData.DoesNotExist:
            pass
        request.session['auto_loaded'] = True

    # -------------------------
    # 初期値の設定
    # -------------------------

    defaults = {
        'satisfaction': 50,
        'energy': 50,
        'growth': 0,
        'fullness': 50,
        'turn': 1,
        'remaining_time': 6,
        'character_state': 'normal',
        'play_count': 0,
        'healthy_food_count': 0,
        'snack_count': 0,
        'room_wallpaper': 'room-default',
        'items': [],
        'placed_items': [],
    }
    for key, val in defaults.items():
        if key not in request.session:
            request.session[key] = val

    # -------------------------
    # セッションから現在値を取得
    # -------------------------

    satisfaction = request.session['satisfaction']
    energy = request.session['energy']
    growth = request.session['growth']
    fullness = request.session['fullness']
    play_count = request.session['play_count']
    healthy_food_count = request.session['healthy_food_count']
    snack_count = request.session['snack_count']
    turn = request.session['turn']
    remaining_time = request.session['remaining_time']
    character_state = request.session['character_state']
    items = request.session['items']
    placed_items = request.session['placed_items']
    room_wallpaper = request.session['room_wallpaper']

    # -------------------------
    # 成長段階ごとの最大時間
    # -------------------------

    if growth < 20:
        max_time = 6
    elif growth < 40:
        max_time = 7
    elif growth < 80:
        max_time = 8
    else:
        max_time = 9

    # -------------------------
    # アクションと基本判定
    # -------------------------

    action = request.GET.get('action')
    game_end = energy <= 0 or growth >= 100

    action_cost = {
        'ball': 2,
        'rest': 2,
        'food_minigame': 1,
        'dodge_minigame': 3,
        'dance_minigame': 1,
        'timing_minigame': 2,
        'count_minigame': 1,
    }

    can_act = (
        action in action_cost
        and remaining_time >= action_cost[action]
        and not game_end
    )

    # -------------------------
    # 全アイテム一覧
    # -------------------------

    all_items = [
        'plant', 'sofa', 'rug', 'clock',
        'room-kawaii', 'room-star', 'room-sky',
        'sofa-star', 'plant-star', 'rug-star', 'clock-star',
        'sofa-kawaii', 'plant-kawaii', 'rug-kawaii', 'clock-kawaii',
    ]

    owned_count = len(items)
    total_count = len(all_items)
    collection_rate = int(owned_count / total_count * 100)

    item_get = False
    get_item_image = ""

    # -------------------------
    # 家具の位置定義
    # -------------------------

    furniture_positions = {
        'sofa':        {'bottom': '20px', 'left': '30px', 'width': '240'},
        'sofa-star':   {'bottom': '40px', 'left': '30px', 'width': '240'},
        'sofa-kawaii': {'bottom': '50px', 'left': '30px', 'width': '240'},
        'plant':       {'bottom': '20px', 'right': '-40px', 'width': '280'},
        'plant-star':  {'bottom': '20px', 'right': '-100px', 'width': '400'},
        'plant-kawaii':{'bottom': '20px', 'right': '-40px', 'width': '280'},
        'rug':         {'bottom': '0px', 'left': '50%', 'transform': 'translateX(-50%)', 'width': '160'},
        'rug-star':    {'bottom': '-10px', 'left': '50%', 'transform': 'translateX(-50%)', 'width': '250'},
        'rug-kawaii':  {'bottom': '-5px', 'left': '50%', 'transform': 'translateX(-50%)', 'width': '160'},
        'clock':       {'top': '20px', 'right': '170px', 'width': '100'},
        'clock-star':  {'top': '20px', 'right': '170px', 'width': '100'},
        'clock-kawaii':{'top': '20px', 'right': '170px', 'width': '100'},
    }

    placed_item_images = []
    for item in placed_items:
        if item.startswith('room-'):
            continue
        position = furniture_positions.get(item, {})
        placed_item_images.append({
            'name': item,
            'image': f'images/{item}.png',
            'top': position.get('top', 'auto'),
            'bottom': position.get('bottom', 'auto'),
            'left': position.get('left', 'auto'),
            'right': position.get('right', 'auto'),
            'transform': position.get('transform', 'none'),
            'width': position.get('width', '120'),
        })

    # -------------------------
    # リセット
    # -------------------------

    if action == "reset":
        if request.user.is_authenticated:
            SaveData.objects.filter(user=request.user).delete()
        request.session['satisfaction'] = 50
        request.session['energy'] = 50
        request.session['growth'] = 0
        request.session['fullness'] = 50
        request.session['turn'] = 1
        request.session['remaining_time'] = 6
        request.session['play_count'] = 0
        request.session['healthy_food_count'] = 0
        request.session['snack_count'] = 0
        request.session['character_state'] = 'normal'
        request.session['room_wallpaper'] = 'room-default'
        request.session['items'] = []
        request.session['placed_items'] = []
        request.session['auto_loaded'] = False
        return redirect('/')

    # -------------------------
    # メニュー処理
    # -------------------------

    menu = request.GET.get('menu', '')

    # 行動後はメニューを閉じる
    if action in [
        'rest', 'next_day',
        'ball_game', 'food_result', 'dodge_result',
        'dance_result', 'timing_result', 'count_result',
    ]:
        menu = ''

    # -------------------------
    # 難易度判定用の成長段階
    # -------------------------

    if growth < 20:
        current_growth_stage = 0
    elif growth < 40:
        current_growth_stage = 1
    elif growth < 80:
        current_growth_stage = 2
    elif growth < 100:
        current_growth_stage = 3
    else:
        current_growth_stage = 4

    difficulty_list = get_difficulty_list(current_growth_stage)

    last_action = action
    food_image = ""

    # -------------------------
    # 難易度の取得ヘルパー
    # -------------------------

    def get_valid_difficulty():
        # URLパラメータから難易度を取得し、未解放なら easy にフォールバック
        diff = request.GET.get("difficulty", "easy")
        unlocked_keys = [d['key'] for d in difficulty_list if d['unlocked']]
        return diff if diff in unlocked_keys else "easy"

    # ================================
    # ミニゲーム結果の処理
    # ================================

    # -------------------------
    # ボールキャッチ終了
    # -------------------------

    if action == "ball_game":

        # JSがscoreMultiplierを掛けたスコアを送ってくるので、そのまま使う
        score = int(request.GET.get("score", 0))
        play_count += 1

        if score < 10:
            satisfaction += 10
            growth += 1
            event_message = "少し遊べた！"
        elif score < 15:
            satisfaction += 20
            growth += 2
            event_message = "たくさん遊べて楽しそう！"
        else:
            satisfaction += 30
            growth += 3
            event_message = "大満足だったみたい！"

        request.session["event_message"] = event_message

    # -------------------------
    # 好きなごはん選び終了
    # -------------------------

    if action == "food_result":

        food_lives = int(request.GET.get("lives", 0))
        healthy_food_count += 1

        if food_lives == 0:
            satisfaction += 5
            energy += 4
            fullness += 5
            event_message = "あまり選べなかった…"
        elif food_lives == 1:
            satisfaction += 8
            energy += 6
            fullness += 8
            event_message = "なんとか食べられた"
        elif food_lives == 2:
            satisfaction += 12
            energy += 9
            fullness += 12
            growth += 1
            event_message = "好物をしっかり選べた！"
        else:
            satisfaction += 20
            energy += 14
            fullness += 18
            growth += 2
            event_message = "完璧に好物だけ選べた！大満足！"

        request.session["event_message"] = event_message

    # -------------------------
    # 障害物よけ終了
    # -------------------------

    if action == "dodge_result":

        dodge_lives = int(request.GET.get("lives", 0))
        dodge_score = int(request.GET.get("score", 0))
        play_count += 1

        if dodge_lives == 0:
            satisfaction += 3
            energy += 4
            fullness -= 15
            event_message = "うまく避けられなかった…"
        elif dodge_lives == 1:
            satisfaction += 6
            energy += 8
            fullness -= 15
            growth += 1
            event_message = "なんとか避けられた！"
        elif dodge_lives == 2:
            satisfaction += 10
            energy += 12
            fullness -= 15
            growth += 2
            event_message = "上手に避けられた！"
        else:
            satisfaction += 14
            energy += 16
            fullness -= 15
            growth += 3
            event_message = "完璧！一度も当たらなかった！"

        if dodge_score >= 5:
            satisfaction += 3
            growth += 1
            event_message += " アイテムもたくさん取れた！"

        request.session["event_message"] = event_message

    # -------------------------
    # ダンスまね終了
    # -------------------------

    if action == "dance_result":

        result = request.GET.get("result", "fail")
        play_count += 1

        difficulty_bonus = {
            'easy': {'growth': 1, 'satisfaction': 8},
            'normal': {'growth': 2, 'satisfaction': 12},
            'hard': {'growth': 3, 'satisfaction': 16},
            'oni': {'growth': 4, 'satisfaction': 20},
        }

        diff = request.GET.get("difficulty", "easy")
        bonus = difficulty_bonus.get(diff, difficulty_bonus['easy'])

        if result == "clear":
            satisfaction += bonus['satisfaction']
            energy -= 5
            fullness -= 5
            growth += bonus['growth']
            event_message = "完璧なダンス！"

        else:
            # 失敗時は難易度に関わらず固定値
            satisfaction += 4
            energy -= 5
            fullness -= 5
            event_message = "惜しかった！また挑戦しよう！"

        request.session["event_message"] = event_message

    # -------------------------
    # 料理タイミング終了
    # -------------------------

    if action == "timing_result":

        timing_lives = int(request.GET.get("lives", 0))
        healthy_food_count += 1

        if timing_lives == 0:
            satisfaction += 2
            energy += 5
            fullness += 10
            event_message = "料理があまりうまくいかなかった…"
        elif timing_lives == 1:
            satisfaction += 4
            energy += 10
            fullness += 20
            growth += 1
            event_message = "なんとか料理できた！"
        elif timing_lives == 2:
            satisfaction += 6
            energy += 15
            fullness += 28
            growth += 2
            event_message = "上手に料理できた！"
        else:
            satisfaction += 10
            energy += 20
            fullness += 35
            growth += 3
            event_message = "完璧な料理ができた！大満足！"

        request.session["event_message"] = event_message

    # -------------------------
    # 食材かぞえ終了
    # -------------------------

    if action == "count_result":

        count_lives = int(request.GET.get("lives", 0))
        snack_count += 1

        if count_lives == 0:
            satisfaction += 8
            energy -= 5
            fullness += 3
            event_message = "食材をうまく数えられなかった…"
        elif count_lives == 1:
            satisfaction += 14
            energy -= 5
            fullness += 5
            growth += 1
            event_message = "なんとか数えられた！"
        elif count_lives == 2:
            satisfaction += 20
            energy -= 5
            fullness += 7
            growth += 1
            event_message = "上手に食材を数えられた！"
        else:
            satisfaction += 28
            energy -= 5
            fullness += 10
            growth += 2
            event_message = "全問正解！食材を完璧に数えられた！"

        request.session["event_message"] = event_message

    # ================================
    # ミニゲーム開始処理（redirect）
    # ================================

    # ボールキャッチ開始
    if action == "ball" and can_act:
        difficulty = get_valid_difficulty()
        remaining_time -= action_cost['ball']
        energy -= 20
        fullness -= 15
        request.session["remaining_time"] = remaining_time
        request.session["energy"] = energy
        request.session["fullness"] = fullness
        return redirect(f"{reverse('ball_game')}?{urlencode({'difficulty': difficulty})}")

    # 好きなごはん選び開始
    elif action == "food_minigame" and can_act:
        difficulty = get_valid_difficulty()
        remaining_time -= action_cost['food_minigame']
        request.session["remaining_time"] = remaining_time
        return redirect(f"{reverse('food_game')}?{urlencode({'difficulty': difficulty})}")

    # ダンスまね開始
    elif action == "dance_minigame" and can_act:
        difficulty = get_valid_difficulty()
        remaining_time -= action_cost['dance_minigame']
        request.session["remaining_time"] = remaining_time
        return redirect(f"{reverse('dance_game')}?{urlencode({'difficulty': difficulty})}")

    # 料理タイミング開始
    elif action == "timing_minigame" and can_act:
        difficulty = get_valid_difficulty()
        remaining_time -= action_cost['timing_minigame']
        request.session["remaining_time"] = remaining_time
        return redirect(f"{reverse('timing_game')}?{urlencode({'difficulty': difficulty})}")

    # 食材かぞえ開始
    elif action == "count_minigame" and can_act:
        difficulty = get_valid_difficulty()
        remaining_time -= action_cost['count_minigame']
        request.session["remaining_time"] = remaining_time
        return redirect(f"{reverse('count_game')}?{urlencode({'difficulty': difficulty})}")

    # 障害物よけ開始
    elif action == "dodge_minigame" and can_act:
        difficulty = get_valid_difficulty()
        remaining_time -= action_cost['dodge_minigame']
        request.session["remaining_time"] = remaining_time
        return redirect(f"{reverse('dodge_game')}?{urlencode({'difficulty': difficulty})}")

    # -------------------------
    # 休む
    # -------------------------

    elif action == 'rest' and can_act:
        if energy <= 20:
            energy += 30
            satisfaction += 10
            remaining_time -= 2
            reaction_state = "good_rest"
        else:
            satisfaction -= 5
            energy += 20
            fullness -= 5
            remaining_time -= 2
            reaction_state = "normal_rest"

    # -------------------------
    # 次の日へ
    # -------------------------

    elif action == 'next_day' and not game_end:
        turn += 1
        if growth < 20:
            remaining_time = 6
        elif growth < 40:
            remaining_time = 7
        elif growth < 80:
            remaining_time = 8
        else:
            remaining_time = 9
        fullness -= 20
        energy += 15
        satisfaction -= 5
        reaction_state = "normal"

    # -------------------------
    # 持ち物の配置・撤去
    # -------------------------

    if action == "place":
        item = request.GET.get("item")
        if item.startswith("room-"):
            request.session["room_wallpaper"] = item
            return redirect("/?menu=items")
        placed_items = request.session.get("placed_items", [])
        new_category = item_categories.get(item)
        for placed_item in placed_items[:]:
            if item_categories.get(placed_item) == new_category:
                placed_items.remove(placed_item)
        placed_items.append(item)
        request.session["placed_items"] = placed_items
        return redirect("/?menu=items")

    if action == 'remove':
        item = request.GET.get('item')
        placed_items = request.session.get('placed_items', [])
        if item in placed_items:
            placed_items.remove(item)
        request.session['placed_items'] = placed_items
        return redirect('/?menu=items')

    # -------------------------
    # 3ターンごとのランダムイベント
    # -------------------------

    if action == 'next_day' and turn % 3 == 0:
        event = random.randint(1, 4)
        if event == 1:
            satisfaction += 20
        elif event == 2:
            energy -= 15
        elif event == 3:
            growth += 2

    # ================================
    # パラメータ依存イベント
    # ================================

    # 初回アクセスはnormal
    if action is None and menu == '':
        character_state = "normal"
    else:
        character_state = request.session.get('character_state', 'normal')

    # ミニゲーム結果・休む・次の日へ のときだけ判定する
    action_list = [
        'rest',
        'next_day',
        'ball_game',
        'food_result',
        'dodge_result',
        'dance_result',
        'timing_result',
        'count_result',
    ]

    if action in action_list:

        # 行動時だけnormalに戻して再判定
        character_state = "normal"

        # 元気が低い
        if energy <= 30:
            growth -= 2
            character_state = "tired"

        # 満足度が高い
        if satisfaction >= 80:
            growth += 1
            character_state = "happy"

        # 満腹すぎる
        if fullness >= 70:
            satisfaction -= 5
            growth -= 2
            character_state = "tired"

        # 満腹なのにごはん系ゲームをした
        if fullness >= 70 and action in ['food_result', 'timing_result', 'count_result']:
            satisfaction -= 10
            energy -= 5
            character_state = "tired"

        # 元気なのに休む
        if energy >= 90 and action == 'rest':
            satisfaction -= 15
            growth -= 2
            character_state = "tired"

        # 疲れているのに遊ぶ
        if energy <= 30 and action in ['ball_game', 'dodge_result', 'dance_result']:
            energy -= 10
            satisfaction -= 5
            character_state = "tired"

        # 空腹なのに遊ぶ
        if fullness <= 30 and action in ['ball_game', 'dodge_result', 'dance_result']:
            satisfaction -= 10
            character_state = "tired"

        # 絶好調
        if satisfaction >= 80 and energy >= 80:
            growth += 2
            character_state = "happy"

        # 弱っている状態
        if energy <= 20 and fullness <= 20:
            growth -= 2
            character_state = "tired"

        # Happyならアイテム獲得チャンス
        if character_state == "happy":
            items = request.session.get('items', [])
            candidate_items = [
                'plant', 'sofa', 'rug', 'clock',
                'room-kawaii', 'room-star', 'room-sky',
                'sofa-star', 'plant-star', 'rug-star', 'clock-star',
                'sofa-kawaii', 'plant-kawaii', 'rug-kawaii', 'clock-kawaii',
            ]
            unlocked = [i for i in candidate_items if i not in items]
            if unlocked and random.randint(1, 100) <= 20:
                new_item = random.choice(unlocked)
                items.append(new_item)
                request.session['items'] = items
                item_get = True
                get_item_image = f'images/{new_item}.png'

    # -------------------------
    # 最終値を制限
    # -------------------------

    satisfaction = max(0, min(100, satisfaction))
    energy = max(0, min(100, energy))
    growth = max(0, min(100, growth))
    fullness = max(0, min(100, fullness))
    remaining_time = max(0, remaining_time)

    # ゲーム終了判定を更新
    game_end = energy <= 0 or growth >= 100

    game_status = ""
    if energy <= 0:
        game_status = "つかれて眠ってしまった…ゲームオーバー"
    elif growth >= 100:
        game_status = "大きく成長した！ゲームクリア！"

    # -------------------------
    # セッション保存
    # -------------------------

    request.session['satisfaction'] = satisfaction
    request.session['energy'] = energy
    request.session['growth'] = growth
    request.session['fullness'] = fullness
    request.session['turn'] = turn
    request.session['event_message'] = event_message
    request.session['character_state'] = character_state
    request.session['remaining_time'] = remaining_time
    request.session['play_count'] = play_count
    request.session['healthy_food_count'] = healthy_food_count
    request.session['snack_count'] = snack_count
    if 'room_wallpaper' not in request.session:
        request.session['room_wallpaper'] = 'room-default'

    # -------------------------
    # 顔タイプを決定
    # -------------------------

    if play_count >= healthy_food_count + 3 and play_count >= snack_count + 3:
        face_type = "-active"
    elif healthy_food_count >= play_count + 3 and healthy_food_count >= snack_count + 3:
        face_type = "-gentle"
    elif snack_count >= play_count + 3 and snack_count >= healthy_food_count + 3:
        face_type = "-cheerful"
    else:
        face_type = ""

    personality_map = {
        "-active":   ("げんきいっぱいタイプ",
                      "たくさん遊んで育てたため、活発で好奇心旺盛な性格に成長しました。"),
        "-gentle":   ("やさしいタイプ",
                      "健康的な食事を大切にしたため、穏やかで思いやりのある性格に成長しました。"),
        "-cheerful": ("むじゃきタイプ",
                      "おやつや楽しい時間を大切にしたため、明るく人なつっこい性格に成長しました。"),
    }
    personality_name, personality_comment = personality_map.get(
        face_type,
        ("バランスタイプ", "さまざまな行動をバランスよく行ったため、なんでも器用にこなせる性格に成長しました。")
    )

    # -------------------------
    # 成長段階を決定
    # -------------------------

    if growth < 20:
        growth_stage = 0
    elif growth < 40:
        growth_stage = 1
    elif growth < 80:
        growth_stage = 2
    elif growth < 100:
        growth_stage = 3
    else:
        growth_stage = 4

    # -------------------------
    # キャラクター画像と状態を決定
    # -------------------------

    state_type = ""
    if growth_stage != 4:
        if character_state == "happy":
            state_type = "-happy"
        elif character_state == "tired":
            state_type = "-tired"

    character_image = f'images/character{growth_stage}{face_type}{state_type}.png'

    # -------------------------
    # アニメーションを決定
    # -------------------------

    animation_map = {
        "happy":  "happyBounce 0.8s ease-in-out infinite",
        "tired":  "tiredMove 3s ease-in-out infinite",
        "hungry": "hungryShake 0.3s linear infinite",
        "full":   "fullMove 4s ease-in-out infinite",
    }
    character_animation = animation_map.get(
        character_state,
        "floatCharacter 2s ease-in-out infinite"
    )

    # -------------------------
    # 背景画像を決定
    # -------------------------

    room_wallpaper = request.session.get('room_wallpaper', 'room-default')
    current_hour = 8 + (max_time - remaining_time) * 2

    if current_hour < 12:
        time_zone = "morning"
    elif current_hour < 18:
        time_zone = "noon"
    else:
        time_zone = "night"

    background_image = f'images/{room_wallpaper}-{time_zone}.png'

    # -------------------------
    # 日付・時刻を計算
    # -------------------------

    current_date = datetime(2026, 4, 1) + timedelta(days=turn - 1)
    date_text = f"{current_date.month}月{current_date.day}日"

    current_hour = 8 + (max_time - remaining_time) * 2
    if current_hour == 12:
        time_text = "正午12:00"
    elif current_hour < 12:
        time_text = f"午前{current_hour}:00"
    elif current_hour == 24:
        time_text = "午前0:00"
    elif current_hour > 24:
        time_text = f"午前{current_hour - 24}:00"
    else:
        time_text = f"午後{current_hour - 12}:00"

    # -------------------------
    # 自動セーブ
    # -------------------------

    if request.user.is_authenticated:
        save_data, created = SaveData.objects.get_or_create(user=request.user)
        save_data.satisfaction = satisfaction
        save_data.energy = energy
        save_data.growth = growth
        save_data.fullness = fullness
        save_data.turn = turn
        save_data.remaining_time = remaining_time
        save_data.play_count = play_count
        save_data.healthy_food_count = healthy_food_count
        save_data.snack_count = snack_count
        save_data.character_state = character_state
        save_data.room_wallpaper = room_wallpaper
        save_data.items = items
        save_data.placed_items = placed_items
        save_data.save()

    status = {
        'satisfaction': satisfaction,
        'energy': energy,
        'growth': growth,
        'fullness': fullness,
        'turn': turn,
        'event_message': event_message,
        'character_image': character_image,
        'game_status': game_status,
        'game_end': game_end,
        'last_action': last_action,
        'character_animation': character_animation,
        'reaction_state': reaction_state,
        'character_state': character_state,
        'food_image': food_image,
        'menu': menu,
        'remaining_time': remaining_time,
        'personality_name': personality_name,
        'personality_comment': personality_comment,
        'date_text': date_text,
        'time_text': time_text,
        'difficulty_list': difficulty_list,
        'item_get': item_get,
        'get_item_image': get_item_image,
        'items': items,
        'all_items': all_items,
        'owned_count': owned_count,
        'total_count': total_count,
        'collection_rate': collection_rate,
        'placed_items': placed_items,
        'placed_item_images': placed_item_images,
        'room_wallpaper': background_image,
        'background_image': background_image,
        'sleep_hours': remaining_time * 2,
        "character_damage_image": f"images/character{growth_stage}-tired.png",
    }

    return render(request, 'turn_based_game/home.html', status)


def debug_view(request):
    status = {
        'satisfaction': request.session.get('satisfaction', 0),
        'energy': request.session.get('energy', 0),
        'growth': request.session.get('growth', 0),
        'fullness': request.session.get('fullness', 0),
        'turn': request.session.get('turn', 0),
        'remaining_time': request.session.get('remaining_time', 0),
    }
    return render(request, 'turn_based_game/debug.html', status)


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


def ball_game(request):

    growth = request.session["growth"]

    if growth < 20:
        growth_stage = 0
    elif growth < 40:
        growth_stage = 1
    elif growth < 80:
        growth_stage = 2
    elif growth < 100:
        growth_stage = 3
    else:
        growth_stage = 4

    difficulty_list = get_difficulty_list(growth_stage)
    selected_difficulty = request.GET.get('difficulty', 'easy')
    unlocked_keys = [d['key'] for d in difficulty_list if d['unlocked']]
    if selected_difficulty not in unlocked_keys:
        selected_difficulty = 'easy'

    DIFFICULTY_SETTINGS = {
        'easy': {'ball_speed': 1.0, 'spawn_interval': 1000, 'score_multiplier': 1},
        'normal': {'ball_speed': 1.4, 'spawn_interval': 800, 'score_multiplier': 1},
        'hard': {'ball_speed': 1.8, 'spawn_interval': 600, 'score_multiplier': 1},
        'oni': {'ball_speed': 2.4, 'spawn_interval': 400, 'score_multiplier': 1},
    }
    current_settings = DIFFICULTY_SETTINGS[selected_difficulty]

    character_image = f"images/character{growth_stage}.png"
    character_happy_image = f"images/character{growth_stage}-happy.png"
    background_image = "images/morning.png"
    ball_image = "images/ball.png"

    status = {
        "growth_stage": growth_stage,
        "character_image": character_image,
        "character_happy_image": character_happy_image,
        "background_image": background_image,
        "game_title": "ボールキャッチ",
        "ball_image": ball_image,
        "selected_difficulty": selected_difficulty,
        "ball_speed": current_settings['ball_speed'],
        "spawn_interval": current_settings['spawn_interval'],
        "score_multiplier": current_settings['score_multiplier'],
    }
    return render(request, "turn_based_game/ball_game.html", status)


def food_game(request):

    growth = request.session["growth"]

    if growth < 20:
        growth_stage = 0
    elif growth < 40:
        growth_stage = 1
    elif growth < 80:
        growth_stage = 2
    elif growth < 100:
        growth_stage = 3
    else:
        growth_stage = 4

    difficulty_list = get_difficulty_list(growth_stage)
    selected_difficulty = request.GET.get('difficulty', 'easy')
    unlocked_keys = [d['key'] for d in difficulty_list if d['unlocked']]
    if selected_difficulty not in unlocked_keys:
        selected_difficulty = 'easy'

    FOOD_DIFFICULTY_SETTINGS = {
        'easy':   {'flow_speed': 1.0, 'spawn_interval': 1200, 'time_limit': 20, 'score_multiplier': 1},
        'normal': {'flow_speed': 1.4, 'spawn_interval': 900,  'time_limit': 18, 'score_multiplier': 1.5},
        'hard':   {'flow_speed': 1.8, 'spawn_interval': 650,  'time_limit': 15, 'score_multiplier': 2},
        'oni':    {'flow_speed': 2.4, 'spawn_interval': 450,  'time_limit': 12, 'score_multiplier': 3},
    }
    current_settings = FOOD_DIFFICULTY_SETTINGS[selected_difficulty]

    character_image = f"images/character{growth_stage}.png"
    character_happy_image = f"images/character{growth_stage}-happy.png"
    background_image = "images/morning.png"

    food_item_images = [
        "images/food1.png",
        "images/food2.png",
        "images/food3.png",
        "images/food4.png",
        "images/food5.png",
        "images/food6.png",
    ]

    status = {
        "growth_stage": growth_stage,
        "character_image": character_image,
        "character_happy_image": character_happy_image,
        "background_image": background_image,
        "game_title": "好きなごはん選び",
        "selected_difficulty": selected_difficulty,
        "flow_speed": current_settings['flow_speed'],
        "spawn_interval": current_settings['spawn_interval'],
        "time_limit": current_settings['time_limit'],
        "score_multiplier": current_settings['score_multiplier'],
        "food_item_images": food_item_images,
        "character_damage_image": f"images/character{growth_stage}-tired.png",
    }
    return render(request, "turn_based_game/food_game.html", status)


def dodge_game(request):

    growth = request.session["growth"]

    if growth < 20:
        growth_stage = 0
    elif growth < 40:
        growth_stage = 1
    elif growth < 80:
        growth_stage = 2
    elif growth < 100:
        growth_stage = 3
    else:
        growth_stage = 4

    difficulty_list = get_difficulty_list(growth_stage)
    selected_difficulty = request.GET.get('difficulty', 'easy')
    unlocked_keys = [d['key'] for d in difficulty_list if d['unlocked']]
    if selected_difficulty not in unlocked_keys:
        selected_difficulty = 'easy'

    DODGE_DIFFICULTY_SETTINGS = {
        'easy':   {'obstacle_count': 2, 'fall_speed': 1.0, 'time_limit': 20},
        'normal': {'obstacle_count': 3, 'fall_speed': 1.4, 'time_limit': 18},
        'hard':   {'obstacle_count': 4, 'fall_speed': 1.8, 'time_limit': 15},
        'oni':    {'obstacle_count': 5, 'fall_speed': 2.4, 'time_limit': 12},
    }
    current_settings = DODGE_DIFFICULTY_SETTINGS[selected_difficulty]

    character_image = f"images/character{growth_stage}.png"
    character_happy_image = f"images/character{growth_stage}-happy.png"
    character_damage_image = f"images/character{growth_stage}-tired.png"
    background_image = "images/morning.png"

    status = {
        "growth_stage": growth_stage,
        "character_image": character_image,
        "character_happy_image": character_happy_image,
        "character_damage_image": character_damage_image,
        "background_image": background_image,
        "game_title": "障害物よけ",
        "selected_difficulty": selected_difficulty,
        "obstacle_count": current_settings['obstacle_count'],
        "fall_speed": current_settings['fall_speed'],
        "time_limit": current_settings['time_limit'],
    }
    return render(request, "turn_based_game/dodge_game.html", status)


def dance_game(request):

    growth = request.session["growth"]

    if growth < 20:
        growth_stage = 0
    elif growth < 40:
        growth_stage = 1
    elif growth < 80:
        growth_stage = 2
    elif growth < 100:
        growth_stage = 3
    else:
        growth_stage = 4

    difficulty_list = get_difficulty_list(growth_stage)
    selected_difficulty = request.GET.get('difficulty', 'easy')
    unlocked_keys = [d['key'] for d in difficulty_list if d['unlocked']]
    if selected_difficulty not in unlocked_keys:
        selected_difficulty = 'easy'

    DANCE_DIFFICULTY_SETTINGS = {
        'easy':   {'sequence_length': 3,  'show_seconds': 4},
        'normal': {'sequence_length': 5,  'show_seconds': 4},
        'hard':   {'sequence_length': 7,  'show_seconds': 5},
        'oni':    {'sequence_length': 10, 'show_seconds': 5},
    }
    current_settings = DANCE_DIFFICULTY_SETTINGS[selected_difficulty]

    character_image = f"images/character{growth_stage}.png"
    character_happy_image = f"images/character{growth_stage}-happy.png"
    character_damage_image = f"images/character{growth_stage}-tired.png"
    background_image = "images/morning.png"

    status = {
        "growth_stage": growth_stage,
        "character_image": character_image,
        "character_happy_image": character_happy_image,
        "character_damage_image": character_damage_image,
        "background_image": background_image,
        "game_title": "ダンスまね",
        "selected_difficulty": selected_difficulty,
        "sequence_length": current_settings['sequence_length'],
        "show_seconds": current_settings['show_seconds'],
    }
    return render(request, "turn_based_game/dance_game.html", status)


def timing_game(request):

    growth = request.session["growth"]

    if growth < 20:
        growth_stage = 0
    elif growth < 40:
        growth_stage = 1
    elif growth < 80:
        growth_stage = 2
    elif growth < 100:
        growth_stage = 3
    else:
        growth_stage = 4

    difficulty_list = get_difficulty_list(growth_stage)
    selected_difficulty = request.GET.get('difficulty', 'easy')
    unlocked_keys = [d['key'] for d in difficulty_list if d['unlocked']]
    if selected_difficulty not in unlocked_keys:
        selected_difficulty = 'easy'

    TIMING_DIFFICULTY_SETTINGS = {
        'easy':   {'round_count': 3, 'speed': 1.0, 'zone_width': 30},
        'normal': {'round_count': 4, 'speed': 1.5, 'zone_width': 22},
        'hard':   {'round_count': 5, 'speed': 2.0, 'zone_width': 15},
        'oni':    {'round_count': 6, 'speed': 2.8, 'zone_width': 10},
    }
    current_settings = TIMING_DIFFICULTY_SETTINGS[selected_difficulty]

    character_image = f"images/character{growth_stage}.png"
    character_happy_image = f"images/character{growth_stage}-happy.png"
    character_damage_image = f"images/character{growth_stage}-tired.png"
    background_image = "images/morning.png"

    status = {
        "growth_stage": growth_stage,
        "character_image": character_image,
        "character_happy_image": character_happy_image,
        "character_damage_image": character_damage_image,
        "background_image": background_image,
        "game_title": "火加減チャレンジ",
        "selected_difficulty": selected_difficulty,
        "round_count": current_settings['round_count'],
        "speed": current_settings['speed'],
        "zone_width": current_settings['zone_width'],
    }
    return render(request, "turn_based_game/timing_game.html", status)


def count_game(request):

    growth = request.session["growth"]

    if growth < 20:
        growth_stage = 0
    elif growth < 40:
        growth_stage = 1
    elif growth < 80:
        growth_stage = 2
    elif growth < 100:
        growth_stage = 3
    else:
        growth_stage = 4

    difficulty_list = get_difficulty_list(growth_stage)
    selected_difficulty = request.GET.get('difficulty', 'easy')
    unlocked_keys = [d['key'] for d in difficulty_list if d['unlocked']]
    if selected_difficulty not in unlocked_keys:
        selected_difficulty = 'easy'

    COUNT_DIFFICULTY_SETTINGS = {
        'easy':   {'round_count': 3, 'display_time': 3000, 'item_count': 6,  'type_count': 2},
        'normal': {'round_count': 4, 'display_time': 2500, 'item_count': 9,  'type_count': 3},
        'hard':   {'round_count': 5, 'display_time': 2000, 'item_count': 12, 'type_count': 4},
        'oni':    {'round_count': 6, 'display_time': 1500, 'item_count': 15, 'type_count': 5},
    }
    current_settings = COUNT_DIFFICULTY_SETTINGS[selected_difficulty]

    character_image = f"images/character{growth_stage}.png"
    character_happy_image = f"images/character{growth_stage}-happy.png"
    character_damage_image = f"images/character{growth_stage}-tired.png"
    background_image = "images/morning.png"

    food_emojis = ["🍎", "🍌", "🍇", "🍓", "🥕", "🌽", "🍳", "🥚", "🧀", "🍗"]

    status = {
        "growth_stage": growth_stage,
        "character_image": character_image,
        "character_happy_image": character_happy_image,
        "character_damage_image": character_damage_image,
        "background_image": background_image,
        "game_title": "食材かぞえ",
        "selected_difficulty": selected_difficulty,
        "round_count": current_settings['round_count'],
        "display_time": current_settings['display_time'],
        "item_count": current_settings['item_count'],
        "type_count": current_settings['type_count'],
        "food_emojis": food_emojis,
    }
    return render(request, "turn_based_game/count_game.html", status)