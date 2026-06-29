from django.shortcuts import render, redirect
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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

    if (
        request.user.is_authenticated
        and not request.session.get('auto_loaded', False)
    ):

        try:
            save_data = SaveData.objects.get(
                user=request.user
            )

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



    # 初回だけ初期値を作る

    if 'satisfaction' not in request.session:
        request.session['satisfaction'] = 50

    if 'energy' not in request.session:
        request.session['energy'] = 50

    if 'growth' not in request.session:
        request.session['growth'] = 0

    if 'fullness' not in request.session:
        request.session['fullness'] = 50

    if 'turn' not in request.session:
        request.session['turn'] = 1

    if 'remaining_time' not in request.session:
        request.session['remaining_time'] = 6

    if 'character_state' not in request.session:
        request.session['character_state'] = 'normal'

    if 'play_count' not in request.session:
        request.session['play_count'] = 0

    if 'healthy_food_count' not in request.session:
        request.session['healthy_food_count'] = 0

    if 'snack_count' not in request.session:
        request.session['snack_count'] = 0

    if 'remaining_time' not in request.session:
        request.session['remaining_time'] = 6

    # 初期壁紙
    if 'room_wallpaper' not in request.session:
        request.session['room_wallpaper'] = 'room-default'

    if 'items' not in request.session:
        request.session['items'] = []

    if 'placed_items' not in request.session:
        request.session['placed_items'] = []

    # セッションから現在値を取得

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



    # 成長段階ごとの最大時間
    if growth < 20:
        max_time = 6  # 12時間

    elif growth < 40:
        max_time = 7  # 14時間

    elif growth < 80:
        max_time = 8  # 16時間

    else:
        max_time = 9  # 18時間

    # ボタン判定
    action = request.GET.get('action')


    # ゲーム終了判定
    game_end = energy <= 0 or growth >= 100

    # 行動ごとの消費時間
    action_cost = {
        'salad': 1,
        'snack': 1,
        'meal': 2,
        'ball': 2,
        'toy': 1,
        'bike': 3,
        'rest': 2,
    }

    # 行動可能か判定
    can_act = (
            action in action_cost
            and remaining_time >= action_cost[action]
            and not game_end
    )

    # 図鑑用の全アイテム一覧
    all_items = [
        'plant',
        'sofa',
        'rug',
        'clock',

        'room-kawaii',
        'room-star',
        'room-sky',

        'sofa-star',
        'plant-star',
        'rug-star',
        'clock-star',

        'sofa-kawaii',
        'plant-kawaii',
        'rug-kawaii',
        'clock-kawaii',
    ]

    owned_count = len(items)
    total_count = len(all_items)

    collection_rate = int(
        owned_count / total_count * 100
    )

    item_get = False
    get_item_image = ""

    furniture_positions = {

        # ソファ系
        'sofa': {
            'bottom': '20px',
            'left': '30px',
            'width': '240'
        },

        'sofa-star': {
            'bottom': '40px',
            'left': '30px',
            'width': '240'
        },

        'sofa-kawaii': {
            'bottom': '50px',
            'left': '30px',
            'width': '240'
        },

        # 植物系
        'plant': {
            'bottom': '20px',
            'right': '-40px',
            'width': '280'
        },

        'plant-star': {
            'bottom': '20px',
            'right': '-100px',
            'width': '400'
        },

        'plant-kawaii': {
            'bottom': '20px',
            'right': '-40px',
            'width': '280'
        },

        # ラグ系
        'rug': {
            'bottom': '0px',
            'left': '50%',
            'transform': 'translateX(-50%)',
            'width': '160'
        },

        'rug-star': {
            'bottom': '-10px',
            'left': '50%',
            'transform': 'translateX(-50%)',
            'width': '250'
        },

        'rug-kawaii': {
            'bottom': '-5px',
            'left': '50%',
            'transform': 'translateX(-50%)',
            'width': '160'
        },

        # 時計系
        'clock': {
            'top': '20px',
            'right': '170px',
            'width': '100'
        },

        'clock-star': {
            'top': '20px',
            'right': '170px',
            'width': '100'
        },

        'clock-kawaii': {
            'top': '20px',
            'right': '170px',
            'width': '100'
        },
    }

    placed_item_images = []

    for item in placed_items:

        # 壁紙は家具一覧に追加しない
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

            'transform': position.get(
                'transform',
                'none'
            ),

            'width': position.get(
                'width',
                '120'
            ),
        })

    item_get = False
    get_item_image = ""

    before_energy = energy
    before_fullness = fullness
    before_satisfaction = satisfaction

    # ボタン判定
    action = request.GET.get('action')

    # -------------------------
    # ボールキャッチ終了
    # -------------------------

    if action == "ball_game":

        score = int(request.GET.get("score", 0))
        difficulty = request.GET.get("difficulty", "easy")

        multiplier_map = {
            'easy': 1,
            'normal': 1.5,
            'hard': 2,
            'oni': 3,
        }
        multiplier = multiplier_map.get(difficulty, 1)

        adjusted_score = score * multiplier

        play_count += 1
        remaining_time -= 2

        if adjusted_score < 10:
            satisfaction += 10
            growth += 1
            event_message = "少し遊べた！"

        elif adjusted_score < 15:
            satisfaction += 20
            growth += 2
            event_message = "たくさん遊べて楽しそう！"

        else:
            satisfaction += 30
            growth += 3
            event_message = "大満足だったみたい！"

        request.session["event_message"] = event_message



    # ゲーム終了判定
    game_end = energy <= 0 or growth >= 100

    # 行動ごとの消費時間
    action_cost = {
        'salad': 1,
        'snack': 1,
        'meal': 2,
        'ball': 2,
        'toy': 1,
        'bike': 3,
        'rest': 2,
    }

    # 行動可能か判定
    can_act = (
            action in action_cost
            and remaining_time >= action_cost[action]
            and not game_end
    )

    # 図鑑用の全アイテム一覧
    all_items = [
        'plant',
        'sofa',
        'rug',
        'clock',

        'room-kawaii',
        'room-star',
        'room-sky',

        'sofa-star',
        'plant-star',
        'rug-star',
        'clock-star',

        'sofa-kawaii',
        'plant-kawaii',
        'rug-kawaii',
        'clock-kawaii',
    ]

    owned_count = len(items)
    total_count = len(all_items)

    collection_rate = int(
        owned_count / total_count * 100
    )

    item_get = False
    get_item_image = ""

    furniture_positions = {

        # ソファ系
        'sofa': {
            'bottom': '20px',
            'left': '30px',
            'width': '240'
        },

        'sofa-star': {
            'bottom': '40px',
            'left': '30px',
            'width': '240'
        },

        'sofa-kawaii': {
            'bottom': '50px',
            'left': '30px',
            'width': '240'
        },

        # 植物系
        'plant': {
            'bottom': '20px',
            'right': '-40px',
            'width': '280'
        },

        'plant-star': {
            'bottom': '20px',
            'right': '-100px',
            'width': '400'
        },

        'plant-kawaii': {
            'bottom': '20px',
            'right': '-40px',
            'width': '280'
        },

        # ラグ系
        'rug': {
            'bottom': '0px',
            'left': '50%',
            'transform': 'translateX(-50%)',
            'width': '160'
        },

        'rug-star': {
            'bottom': '-10px',
            'left': '50%',
            'transform': 'translateX(-50%)',
            'width': '250'
        },

        'rug-kawaii': {
            'bottom': '-5px',
            'left': '50%',
            'transform': 'translateX(-50%)',
            'width': '160'
        },

        # 時計系
        'clock': {
            'top': '20px',
            'right': '170px',
            'width': '100'
        },

        'clock-star': {
            'top': '20px',
            'right': '170px',
            'width': '100'
        },

        'clock-kawaii': {
            'top': '20px',
            'right': '170px',
            'width': '100'
        },
    }

    placed_item_images = []

    for item in placed_items:

        # 壁紙は家具一覧に追加しない
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

            'transform': position.get(
                'transform',
                'none'
            ),

            'width': position.get(
                'width',
                '120'
            ),
        })

    item_get = False
    get_item_image = ""

    before_energy = energy
    before_fullness = fullness
    before_satisfaction = satisfaction

    # ボタン判定
    action = request.GET.get('action')


    # リセット
    if action == "reset":

        if request.user.is_authenticated:
            SaveData.objects.filter(
                user=request.user
            ).delete()

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

    menu = request.GET.get('menu', '')

    # 行動後はメニューを閉じる
    if action in [
        'salad', 'snack', 'meal',
        'ball', 'toy', 'bike',
        'rest', 'next_day'
    ]:
        menu = ''

    # 難易度判定用の成長段階
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

    # 最後の行動
    last_action = action

    food_image = ""


    # -------------------------
    # ごはん系
    # -------------------------

    # サラダ
    if action == 'salad' and can_act:

        healthy_food_count += 1

        satisfaction += 10
        energy += 8
        fullness += 10

        remaining_time -= 1



    # おやつ
    elif action == 'snack' and can_act:

        snack_count += 1

        satisfaction += 25
        energy -= 5
        fullness += 8

        remaining_time -= 1



    # 肉
    elif action == 'meal' and can_act:

        satisfaction += 5
        energy += 15
        fullness += 30
        growth += 2

        remaining_time -= 2

        reaction_state = "normal_food"


    # -------------------------
    # あそぶ系
    # -------------------------

    elif action == "ball" and can_act:

        difficulty = request.GET.get("difficulty", "easy")

        # 未解放の難易度が指定された場合はeasyにフォールバック

        unlocked_keys = [

            d['key'] for d in difficulty_list if d['unlocked']

        ]

        if difficulty not in unlocked_keys:
            difficulty = "easy"

        remaining_time -= 2

        energy -= 20

        fullness -= 15

        request.session["remaining_time"] = remaining_time

        request.session["energy"] = energy

        request.session["fullness"] = fullness

        query = urlencode({"difficulty": difficulty})

        return redirect(f"{reverse('ball_game')}?{query}")



    elif action == 'toy' and can_act:

        play_count += 1

        satisfaction += 10
        energy -= 5
        fullness -= 5
        growth += 2

        remaining_time -= 1

        reaction_state = "normal_play"



    elif action == 'bike' and can_act:

        play_count += 1

        satisfaction += 8
        energy += 12
        fullness -= 15
        growth += 1

        remaining_time -= 3

        reaction_state = "normal_play"



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


    #次の日へ
    elif action == 'next_day' and not game_end:

        turn += 1

        # 成長段階で行動時間増加
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


    # 持ち物
    if action == "place":

        item = request.GET.get("item")

        # 壁紙の場合
        if item.startswith("room-"):
            request.session["room_wallpaper"] = item

            return redirect("/?menu=items")

        # 家具の場合
        placed_items = request.session.get(
            "placed_items",
            []
        )

        new_category = item_categories.get(item)

        for placed_item in placed_items[:]:

            placed_category = item_categories.get(
                placed_item
            )

            if placed_category == new_category:
                placed_items.remove(placed_item)


        # （カテゴリ重複チェックなど）

        placed_items.append(item)

        request.session["placed_items"] = placed_items

        return redirect("/?menu=items")




    if action == 'remove':

        item = request.GET.get('item')

        placed_items = request.session.get(
            'placed_items',
            []
        )

        if item in placed_items:
            placed_items.remove(item)

        request.session['placed_items'] = placed_items

        return redirect('/?menu=items')



    # 3ターンごとのランダムイベント
    if action == 'next_day' and turn % 3 == 0:

        event = random.randint(1, 4)

        # 楽しいことがあった
        if event == 1:
            satisfaction += 20


        # 疲れた
        elif event == 2:
            energy -= 15


        # 成長
        elif event == 3:
            growth += 2






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

        # 満腹なのにごはん
        if (
                fullness >= 70
                and action in ['salad', 'snack', 'meal']
        ):
            satisfaction -= 10
            energy -= 5
            character_state = "tired"

        # 元気なのに休む
        if energy >= 90 and action == 'rest':
            satisfaction -= 15
            growth -= 2
            character_state = "tired"

        # 疲れているのに遊ぶ
        if (
                energy <= 30
                and action in ['ball', 'toy', 'bike']
        ):
            energy -= 10
            satisfaction -= 5
            character_state = "tired"

        # 空腹なのに遊ぶ
        if (
                fullness <= 30
                and action in ['ball', 'toy', 'bike']
        ):
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

        # 最終的にHappyならアイテム獲得
        if character_state == "happy":

            items = request.session.get('items', [])

            candidate_items = [
                'plant',
                'sofa',
                'rug',
                'clock',
                'room-kawaii',
                'room-star',
                'room-sky',
                'sofa-star',
                'plant-star',
                'rug-star',
                'clock-star',
                'sofa-kawaii',
                'plant-kawaii',
                'rug-kawaii',
                'clock-kawaii',
            ]

            unlocked = [
                item for item in candidate_items
                if item not in items
            ]

            roll = random.randint(1, 100)
            print("抽選結果 =", roll)
            print("unlocked =", unlocked)

            if unlocked and random.randint(1, 100) <= 20:
                new_item = random.choice(unlocked)

                items.append(new_item)
                request.session['items'] = items

                item_get = True
                get_item_image = f'images/{new_item}.png'


    # 最終値を制限
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



    # セッション保存
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

    print("energy", energy)
    print("fullness", fullness)
    print("satisfaction", satisfaction)



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

    personality_name = ""
    personality_comment = ""

    if face_type == "-active":
        personality_name = "げんきいっぱいタイプ"
        personality_comment = (
            "たくさん遊んで育てたため、"
            "活発で好奇心旺盛な性格に成長しました。"
        )

    elif face_type == "-gentle":
        personality_name = "やさしいタイプ"
        personality_comment = (
            "健康的な食事を大切にしたため、"
            "穏やかで思いやりのある性格に成長しました。"
        )

    elif face_type == "-cheerful":
        personality_name = "むじゃきタイプ"
        personality_comment = (
            "おやつや楽しい時間を大切にしたため、"
            "明るく人なつっこい性格に成長しました。"
        )

    else:
        personality_name = "バランスタイプ"
        personality_comment = (
            "さまざまな行動をバランスよく行ったため、"
            "なんでも器用にこなせる性格に成長しました。"
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
    # 状態を決定
    # -------------------------

    state_type = ""

    # 最終形態以外のみ状態変化を反映
    if growth_stage != 4:

        if character_state == "happy":
            state_type = "-happy"

        elif character_state == "tired":
            state_type = "-tired"

    # -------------------------
    # キャラクター画像を決定
    # -------------------------

    character_image = (
        f'images/character{growth_stage}{face_type}{state_type}.png'
    )

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


    # 実際の背景画像を作成
    room_wallpaper = request.session.get(
        'room_wallpaper',
        'room-default'
    )

    current_hour = 8 + (max_time - remaining_time) * 2

    if current_hour < 12:
        time_zone = "morning"

    elif current_hour < 18:
        time_zone = "noon"

    else:
        time_zone = "night"

    background_image = (
        f'images/{room_wallpaper}-{time_zone}.png'
    )



    print("item_get =", item_get)
    print("character_state =", character_state)
    print("items =", request.session.get('items', []))
    print("placed_items =", request.session.get('placed_items', []))
    print(request.session.get('room_wallpaper'))
    print(request.session['room_wallpaper'])
    print(background_image)


    start_date = datetime(2026, 4, 1)

    current_date = datetime(2026, 4, 1) + timedelta(days=turn - 1)

    date_text = f"{current_date.month}月{current_date.day}日"


    # 現在時刻を計算
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

    sleep_hours = remaining_time * 2

    # -------------------------
    # 自動セーブ
    # -------------------------

    if request.user.is_authenticated:
        save_data, created = SaveData.objects.get_or_create(
            user=request.user
        )

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


    }

    return render(
        request,
        'turn_based_game/home.html',
        status
    )



def debug_view(request):
    status = {
        'satisfaction': request.session.get('satisfaction', 0),
        'energy': request.session.get('energy', 0),
        'growth': request.session.get('growth', 0),
        'fullness': request.session.get('fullness', 0),

        'turn': request.session.get('turn', 0),
        'remaining_time': request.session.get('remaining_time', 0),
    }

    return render(
        request,
        'turn_based_game/debug.html',
        status
    )


def signup(request):

    if request.method == 'POST':

        form = SignUpForm(request.POST)

        if form.is_valid():

            user = form.save()

            login(request, user)

            return redirect('/')

    else:
        form = SignUpForm()

    return render(
        request,
        'registration/signup.html',
        {'form': form}
    )

def ball_game(request):

    # -------------------------
    # 成長度を取得
    # -------------------------

    # セッションから現在の成長度を取得
    growth = request.session["growth"]

    # -------------------------
    # 成長段階を判定
    # -------------------------

    # 成長度に応じて成長段階（0〜4）を決定
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
    # 難易度の解放状況を取得
    # -------------------------

    # 成長段階に応じて、どの難易度が解放されているかを取得
    difficulty_list = get_difficulty_list(growth_stage)

    # -------------------------
    # 選択された難易度を取得
    # -------------------------

    # URLのクエリパラメータから難易度を取得（未指定ならeasy）
    selected_difficulty = request.GET.get('difficulty', 'easy')

    # 現在解放されている難易度キーの一覧を作成
    unlocked_keys = [d['key'] for d in difficulty_list if d['unlocked']]

    # 未解放の難易度が指定されていた場合はeasyにフォールバック
    if selected_difficulty not in unlocked_keys:
        selected_difficulty = 'easy'

    # -------------------------
    # 難易度ごとのゲームパラメータを定義
    # -------------------------

    # ball_speed：ボールの再配置の速さ
    # spawn_interval：自動でボールが動く間隔（ミリ秒）
    # score_multiplier：スコアにかける倍率
    DIFFICULTY_SETTINGS = {
        'easy':   {'ball_speed': 1.0, 'spawn_interval': 1000, 'score_multiplier': 1},
        'normal': {'ball_speed': 1.4, 'spawn_interval': 800,  'score_multiplier': 1.5},
        'hard':   {'ball_speed': 1.8, 'spawn_interval': 600,  'score_multiplier': 2},
        'oni':    {'ball_speed': 2.4, 'spawn_interval': 400,  'score_multiplier': 3},
    }

    # 選択された難易度に対応する設定値を取り出す
    current_settings = DIFFICULTY_SETTINGS[selected_difficulty]

    # -------------------------
    # 使用する画像を設定
    # -------------------------

    # 成長段階に応じた通常画像
    character_image = f"images/character{growth_stage}.png"

    # 成長段階に応じたHappy画像
    character_happy_image = f"images/character{growth_stage}-happy.png"

    # 背景画像
    background_image = "images/morning.png"

    # ボール画像
    ball_image = "images/ball.png"

    # -------------------------
    # テンプレートへ渡すデータ
    # -------------------------

    status = {
        "growth_stage": growth_stage,
        "character_image": character_image,
        "character_happy_image": character_happy_image,
        "background_image": background_image,
        "game_title": "ボールキャッチ",
        "ball_image": ball_image,

        # 選択された難易度と、それに応じたゲームパラメータ
        "selected_difficulty": selected_difficulty,
        "ball_speed": current_settings['ball_speed'],
        "spawn_interval": current_settings['spawn_interval'],
        "score_multiplier": current_settings['score_multiplier'],
    }

    # -------------------------
    # ボールキャッチ画面を表示
    # -------------------------

    return render(
        request,
        "turn_based_game/ball_game.html",
        status
    )