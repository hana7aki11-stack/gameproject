from django.shortcuts import render, redirect
import random
from datetime import datetime, timedelta
from urllib.parse import urlencode
from .models import SaveData, ActionLog
from django.contrib.auth import login
from .forms import SignUpForm
from django.urls import reverse
from django.utils import timezone



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

def get_int(request, name, default=0):
    # URLの数値を安全に取得（変な値が来ても落ちない）
    try:
        return int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default


# アイテムの表示名
ITEM_NAMES = {
    'plant': '観葉植物', 'sofa': 'ソファ', 'rug': 'ラグ', 'clock': '時計',
    'room-kawaii': 'かわいい壁紙', 'room-star': '星空の壁紙', 'room-sky': '空の壁紙',
    'sofa-star': '星のソファ', 'plant-star': '星の観葉植物',
    'rug-star': '星のラグ', 'clock-star': '星の時計',
    'sofa-kawaii': 'かわいいソファ', 'plant-kawaii': 'かわいい観葉植物',
    'rug-kawaii': 'かわいいラグ', 'clock-kawaii': 'かわいい時計',
}

# キャラクターのセリフ（理由は言わず、ヒントだけ出す）
HINT_TEXTS = {
    'hungry': ["なんだかそわそわするな……", "……ぐぅ〜"],
    'tired':  ["なんだか元気が出ないな……", "ふあぁ……"],
    'full':   ["ふぅ……ちょっと動きたくないなあ", "うぅ……"],
    'bored':  ["なんだかつまらないな〜……", "ねえねえ、なにかしようよ"],
    'happy':  ["ふふっ♪", "えへへ、たのしいな！"],
    'normal': ["どうしたの？", "なあに？"],
}


def get_hint_type(energy, fullness, satisfaction):
    # パラメータからセリフの種類を決める（上にあるほど優先）
    if fullness <= 30:
        return 'hungry'
    if energy <= 30:
        return 'tired'
    if fullness >= 90:
        return 'full'
    if satisfaction <= 30:
        return 'bored'
    if satisfaction >= 80:
        return 'happy'
    return 'normal'


# チュートリアルの文言（(ステップ, 今どこを案内しているか) ごと）
TUTORIAL_TEXTS = {
    (1, 'main'):    "STEP 1　ごはん\nおなかがすいているみたいです。\n「ごはん」を押してね。",
    (1, 'submenu'): "STEP 1　ごはん\nまずは「好きなごはん選び」を選んでみよう！",
    (1, 'level'):   "STEP 1　ごはん\nむずかしさは「かんたん」を選んでね。",
    (2, 'main'):    "STEP 2　あそぶ\n元気があるときは、一緒に遊んでみましょう！\n「あそぶ」を押してね。",
    (2, 'submenu'): "STEP 2　あそぶ\nまずは「ダンスまね」を選んでみよう！",
    (2, 'level'):   "STEP 2　あそぶ\nむずかしさは「かんたん」を選んでね。",
    (3, 'rest'):    "STEP 3　休む\n疲れたときは休ませてあげましょう。\n「休む」を押してみてね。",
}

# チュートリアルで強制するミニゲーム
TUTORIAL_PARENT_MENU = {1: 'food', 2: 'play'}                       # ごはん／あそぶ
TUTORIAL_FORCED_MENU = {1: 'food_difficulty', 2: 'dance_difficulty'} # 選ばせるゲーム
TUTORIAL_FORCED_ACTION = {1: 'food_minigame', 2: 'dance_minigame'}   # 開始アクション
TUTORIAL_DONE_LINES = {
    1: "✓ おなかいっぱいになりました！",
    2: "✓ 上手に遊べました！",
    3: "✓ ゆっくり休んで元気になりました！",
}
TUTORIAL_END_TEXT = "チュートリアル完了！\nここからは、この子の様子をよく見ながら育ててみてね。"

FOOD_RESULT_ACTIONS = ['food_result', 'timing_result', 'count_result']
PLAY_RESULT_ACTIONS = ['ball_game', 'dodge_result', 'dance_result']

# ミニゲーム結果によるパラメータ変化（残りライフ0〜3の順）
# (満足度, 元気, 満腹度, 成長, メッセージ)  ← バランス調整はここの数字だけでOK
RESULT_TABLES = {
    'food': [   # 好きなごはん選び（旧サラダ）
        (5, 2, 12, 0, "あまり選べなかった…"),
        (8, 3, 18, 0, "なんとか食べられた"),
        (12, 4, 24, 1, "好物をしっかり選べた！"),
        (20, 5, 30, 2, "完璧に好物だけ選べた！大満足！"),
    ],
    'timing': [  # 火加減チャレンジ（旧お肉）
        (2, 3, 15, 0, "料理があまりうまくいかなかった…"),
        (4, 6, 25, 1, "なんとか料理できた！"),
        (6, 9, 35, 2, "上手に料理できた！"),
        (10, 12, 45, 3, "完璧な料理ができた！大満足！"),
    ],
    'count': [   # 食材かぞえ（旧おやつ）
        (8, -2, 5, 0, "食材をうまく数えられなかった…"),
        (14, -2, 8, 1, "なんとか数えられた！"),
        (20, -2, 10, 1, "上手に食材を数えられた！"),
        (28, -2, 14, 2, "全問正解！食材を完璧に数えられた！"),
    ],
    'dodge': [   # 障害物よけ（運動なので元気が減る）
        (3, -15, -10, 0, "うまく避けられなかった…"),
        (6, -12, -10, 1, "なんとか避けられた！"),
        (10, -10, -10, 2, "上手に避けられた！"),
        (14, -8, -10, 3, "完璧！一度も当たらなかった！"),
    ],
}
LIVES_GAMES = {
    'food_result': 'food', 'timing_result': 'timing',
    'count_result': 'count', 'dodge_result': 'dodge',
}

# ダンスまねのクリア報酬（満足度, 成長）
DANCE_CLEAR_TABLE = {
    'easy': (8, 1), 'normal': (12, 2), 'hard': (16, 3), 'oni': (20, 4),
}


# 「2回目以降のニューゲーム」でイントロ／チュートリアルを選ばせるか
#   False: ニューゲームのたびに必ず最初から見せる
#   True : 一度チュートリアルを終えた人には「見る／スキップ」を選ばせる
ASK_TUTORIAL_ON_REPEAT = False

# 行動ごとの消費時間（時間）
ACTION_COST = {
    'ball': 4, 'rest': 4, 'food_minigame': 2, 'dodge_minigame': 6,
    'dance_minigame': 2, 'timing_minigame': 4, 'count_minigame': 2,
}

# 開始アクション → 移動先の画面
START_VIEWS = {
    'ball': 'ball_game', 'food_minigame': 'food_game',
    'dance_minigame': 'dance_game', 'timing_minigame': 'timing_game',
    'count_minigame': 'count_game', 'dodge_minigame': 'dodge_game',
}

# 開始アクション → 結果アクション（結果URLを1回だけ有効にするため）
RESULT_FOR_START = {
    'ball': 'ball_game', 'food_minigame': 'food_result',
    'dance_minigame': 'dance_result', 'timing_minigame': 'timing_result',
    'count_minigame': 'count_result', 'dodge_minigame': 'dodge_result',
}
RESULT_ACTIONS = list(RESULT_FOR_START.values())

# メニューの並び（メニュー名, 表示名, 開始アクション, 消費時間）
FOOD_MENU = [
    ('food_difficulty', '好きなごはん選び', 'food_minigame', 2),
    ('timing_difficulty', '火加減チャレンジ', 'timing_minigame', 4),
    ('count_difficulty', '食材かぞえ', 'count_minigame', 2),
]
PLAY_MENU = [
    ('dance_difficulty', 'ダンスまね', 'dance_minigame', 2),
    ('ball_difficulty', 'ボールキャッチ', 'ball', 4),
    ('dodge_difficulty', '障害物よけ', 'dodge_minigame', 6),
]
# 難易度メニュー名 → (開始アクション, 消費時間)
DIFFICULTY_MENUS = {m: (a, c) for m, _label, a, c in FOOD_MENU + PLAY_MENU}

ALL_ITEMS = [
    'plant', 'sofa', 'rug', 'clock',
    'room-kawaii', 'room-star', 'room-sky',
    'sofa-star', 'plant-star', 'rug-star', 'clock-star',
    'sofa-kawaii', 'plant-kawaii', 'rug-kawaii', 'clock-kawaii',
]

FURNITURE_POSITIONS = {
    'sofa':         {'bottom': '20px', 'left': '30px', 'width': '240'},
    'sofa-star':    {'bottom': '40px', 'left': '30px', 'width': '240'},
    'sofa-kawaii':  {'bottom': '50px', 'left': '30px', 'width': '240'},
    'plant':        {'bottom': '20px', 'right': '-40px', 'width': '280'},
    'plant-star':   {'bottom': '20px', 'right': '-100px', 'width': '400'},
    'plant-kawaii': {'bottom': '20px', 'right': '-40px', 'width': '280'},
    'rug':          {'bottom': '0px', 'left': '50%', 'transform': 'translateX(-50%)', 'width': '160'},
    'rug-star':     {'bottom': '-10px', 'left': '50%', 'transform': 'translateX(-50%)', 'width': '250'},
    'rug-kawaii':   {'bottom': '-5px', 'left': '50%', 'transform': 'translateX(-50%)', 'width': '160'},
    'clock':        {'top': '20px', 'right': '170px', 'width': '100'},
    'clock-star':   {'top': '20px', 'right': '170px', 'width': '100'},
    'clock-kawaii': {'top': '20px', 'right': '170px', 'width': '100'},
}


def make_defaults():
    # 新しい育成の初期値（毎回新しいリストを作る）
    return {
        'satisfaction': 50, 'energy': 50, 'growth': 0, 'fullness': 50,
        'turn': 1, 'remaining_time': 12, 'character_state': 'normal',
        'play_count': 0, 'healthy_food_count': 0, 'snack_count': 0,
        'room_wallpaper': 'room-default', 'items': [], 'placed_items': [],
        'tutorial_step': 0, 'new_items': [], 'notified_stage': 0,
    }


def get_growth_stage(growth):
    if growth < 20:
        return 0
    if growth < 40:
        return 1
    if growth < 80:
        return 2
    if growth < 100:
        return 3
    return 4


def get_max_time(growth):
    # 成長段階ごとの1日の時間
    if growth < 20:
        return 12
    if growth < 40:
        return 14
    if growth < 80:
        return 16
    return 18




def home(request):

    event_message = ""
    reaction_state = "normal"
    tutorial_text = ""

    # -------------------------
    # セーブデータ（ログイン中のみ）
    # -------------------------

    save_data = None
    if request.user.is_authenticated:
        save_data, _ = SaveData.objects.get_or_create(user=request.user)

    action = request.GET.get('action')

    # -------------------------
    # ニューゲーム（ログインの有無に関係なく必ず初期化する）
    # -------------------------

    if action == "reset":

        # すでにチュートリアルを終えているか（リセット前のセッションで判断）
        seen_tutorial = request.session.get('tutorial_step', 0) >= 4
        ask_choice = ASK_TUTORIAL_ON_REPEAT and seen_tutorial

        # セッションを初期値に戻す
        for key, val in make_defaults().items():
            request.session[key] = val
        request.session['tutorial_choice_required'] = ask_choice
        request.session['pending_result'] = ''
        request.session['session_start'] = timezone.now().isoformat()
        request.session['auto_loaded'] = True

        # セーブデータも初期化（ActionLogと累計回数は残す）
        if save_data is not None:
            save_data.satisfaction = 50
            save_data.energy = 50
            save_data.growth = 0
            save_data.fullness = 50
            save_data.turn = 1
            save_data.remaining_time = 12
            save_data.play_count = 0
            save_data.healthy_food_count = 0
            save_data.snack_count = 0
            save_data.character_state = 'normal'
            save_data.room_wallpaper = 'room-default'
            save_data.items = []
            save_data.placed_items = []
            save_data.new_items = []
            save_data.notified_stage = 0
            save_data.tutorial_step = 0
            save_data.has_started_game = True
            save_data.play_session_count += 1
            save_data.play_started_at = timezone.now()
            save_data.save()

        return redirect('/')

    # -------------------------
    # チュートリアルを「見る」／「スキップ」
    # -------------------------

    if action == "tutorial_view":
        request.session['tutorial_choice_required'] = False
        request.session['tutorial_step'] = 0
        if save_data is not None:
            save_data.tutorial_step = 0
            save_data.save()
        return redirect('/')

    if action == "tutorial_skip":
        request.session['tutorial_choice_required'] = False
        request.session['tutorial_step'] = 4
        if save_data is not None:
            save_data.tutorial_step = 4
            save_data.save()
        return redirect('/')

    # -------------------------
    # 自動ロード（セッション開始時に1回だけ）
    # -------------------------

    if save_data is not None and not request.session.get('auto_loaded', False):
        for key in make_defaults().keys():
            request.session[key] = getattr(save_data, key)

        save_data.play_session_count += 1
        if not save_data.play_started_at:
            save_data.play_started_at = timezone.now()
        save_data.save()

        request.session['session_start'] = timezone.now().isoformat()
        request.session['auto_loaded'] = True

    # 足りない項目は初期値で埋める
    for key, val in make_defaults().items():
        if key not in request.session:
            request.session[key] = val

    # -------------------------
    # 現在値
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
    tutorial_step = request.session['tutorial_step']
    notified_stage = request.session['notified_stage']
    new_items = list(request.session['new_items'])

    # 行動前の状態（ログ・反応の判定用）
    before_energy = energy
    before_growth = growth
    before_hint = get_hint_type(energy, fullness, satisfaction)

    max_time = get_max_time(growth)

    # -------------------------
    # 結果URLは「ゲーム開始直後の1回だけ」有効
    # （再読み込み・戻る／進む・URL直打ちで二重に反映されるのを防ぐ）
    # -------------------------

    if action in RESULT_ACTIONS:
        if request.session.get('pending_result') == action:
            request.session['pending_result'] = ''
        else:
            action = None

    game_end = energy <= 0 or growth >= 100

    # チュートリアル中（STEP1〜3）は時間を消費しない
    in_tutorial = tutorial_step in (1, 2, 3)
    was_tutorial = in_tutorial   # ログ用

    can_act = (
        action in ACTION_COST
        and not game_end
        and (in_tutorial or remaining_time >= ACTION_COST[action])
    )

    # チュートリアル中は、指定されたミニゲームしか始められない
    if in_tutorial and action in START_VIEWS:
        if action != TUTORIAL_FORCED_ACTION.get(tutorial_step):
            can_act = False

    owned_count = len(items)
    total_count = len(ALL_ITEMS)
    collection_rate = int(owned_count / total_count * 100)

    item_get = False
    get_item_image = ""
    get_item_name = ""

    # -------------------------
    # メニュー
    # -------------------------

    menu = request.GET.get('menu', '')
    if action in ['rest', 'next_day', 'intro_done'] + RESULT_ACTIONS:
        menu = ''

    difficulty_list = get_difficulty_list(get_growth_stage(growth))
    last_action = action

    def get_valid_difficulty():
        # チュートリアル中は必ず「かんたん」
        if in_tutorial:
            return "easy"
        # 未解放の難易度が指定されたら easy にする
        diff = request.GET.get("difficulty", "easy")
        unlocked_keys = [d['key'] for d in difficulty_list if d['unlocked']]
        return diff if diff in unlocked_keys else "easy"

    def record_minigame(key, success):
        # ミニゲームの累計ログ（保存は最後にまとめて行う）
        if save_data is None:
            return
        for field, add in [
            (f'action_{key}_count', 1),
            (f'minigame_{key}_play', 1),
            (f'minigame_{key}_success', 1 if success else 0),
        ]:
            setattr(save_data, field, getattr(save_data, field) + add)

    # ================================
    # イントロ終了 → チュートリアル開始
    # ================================

    if action == 'intro_done' and tutorial_step == 0:
        tutorial_step = 1
        fullness = 25   # 「おなかがすいている」状態から始める（セリフのヒントも出る）

    # ================================
    # ミニゲーム結果の処理
    # ================================

    # ボールキャッチ（スコア制）
    if action == "ball_game":
        score = get_int(request, "score")
        play_count += 1
        record_minigame('ball', score >= 10)

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

    # ライフ制のゲーム（ごはん選び・火加減・食材かぞえ・障害物よけ）
    if action in LIVES_GAMES:
        key = LIVES_GAMES[action]
        lives = max(0, min(3, get_int(request, "lives")))
        d_sat, d_energy, d_full, d_growth, event_message = RESULT_TABLES[key][lives]

        satisfaction += d_sat
        energy += d_energy
        fullness += d_full
        growth += d_growth

        # 性格タイプ用のカウント
        if key in ('food', 'timing'):
            healthy_food_count += 1
        elif key == 'count':
            snack_count += 1
        else:
            play_count += 1

        # 障害物よけはアイテム5個以上でボーナス
        if key == 'dodge' and get_int(request, "score") >= 5:
            satisfaction += 3
            growth += 1
            event_message += " アイテムもたくさん取れた！"

        record_minigame(key, lives >= 1)

    # ダンスまね
    if action == "dance_result":
        result = request.GET.get("result", "fail")
        play_count += 1
        record_minigame('dance', result == "clear")

        energy -= 8
        fullness -= 8
        if result == "clear":
            bonus_sat, bonus_growth = DANCE_CLEAR_TABLE.get(
                request.GET.get("difficulty", "easy"), (8, 1)
            )
            satisfaction += bonus_sat
            growth += bonus_growth
            event_message = "完璧なダンス！"
        else:
            satisfaction += 4
            event_message = "惜しかった！また挑戦しよう！"

    # ================================
    # ミニゲーム開始（ゲーム画面へ移動）
    # ================================

    if action in START_VIEWS and can_act:
        difficulty = get_valid_difficulty()

        # チュートリアル中は時間・体力を消費しない
        if not in_tutorial:
            remaining_time -= ACTION_COST[action]
            if action == 'ball':
                energy = max(0, energy - 10)
                fullness = max(0, fullness - 10)

        request.session["remaining_time"] = remaining_time
        request.session["energy"] = energy
        request.session["fullness"] = fullness
        request.session["pending_result"] = RESULT_FOR_START[action]

        return redirect(
            f"{reverse(START_VIEWS[action])}?{urlencode({'difficulty': difficulty})}"
        )

    # -------------------------
    # 休む
    # -------------------------

    if action == 'rest' and can_act:
        if save_data is not None:
            save_data.action_rest_count += 1

        if energy <= 40:
            # 疲れているときはよく回復する
            energy += 35
            satisfaction += 8
            reaction_state = "good_rest"
        else:
            energy += 25
            reaction_state = "normal_rest"

        if not in_tutorial:
            fullness -= 3
            remaining_time -= ACTION_COST['rest']

    # -------------------------
    # 次の日へ
    # -------------------------

    if action == 'next_day' and not game_end and not in_tutorial:
        turn += 1
        if save_data is not None:
            save_data.action_next_day_count += 1

        remaining_time = get_max_time(growth)
        fullness -= 15
        energy += 15
        satisfaction -= 5
        reaction_state = "normal"

        # 3ターンごとのランダムイベント
        if turn % 3 == 0:
            event = random.randint(1, 4)
            if event == 1:
                satisfaction += 20
            elif event == 2:
                energy -= 15
            elif event == 3:
                growth += 2

    # -------------------------
    # 持ち物の配置・撤去
    # -------------------------

    if action == "place":
        item = request.GET.get("item", "")
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
        item = request.GET.get('item', '')
        placed_items = request.session.get('placed_items', [])
        if item in placed_items:
            placed_items.remove(item)
        request.session['placed_items'] = placed_items
        return redirect('/?menu=items')

    # -------------------------
    # チュートリアルの進行
    # -------------------------

    done_line = ""
    if tutorial_step == 1 and action in FOOD_RESULT_ACTIONS:
        done_line = TUTORIAL_DONE_LINES[1]
        tutorial_step = 2
    elif tutorial_step == 2 and action in PLAY_RESULT_ACTIONS:
        done_line = TUTORIAL_DONE_LINES[2]
        tutorial_step = 3
    elif tutorial_step == 3 and action == 'rest':
        done_line = TUTORIAL_DONE_LINES[3]
        tutorial_step = 4
        reaction_state = "good_rest"

    # いま画面のどこを案内するか
    tutorial_target = ''
    if tutorial_step in (1, 2):
        if menu == TUTORIAL_PARENT_MENU[tutorial_step]:
            tutorial_target = 'submenu'  # ごはん／あそぶの中身を開いている
        elif menu == TUTORIAL_FORCED_MENU[tutorial_step]:
            tutorial_target = 'level'  # 難易度を選ぶ画面
        else:
            tutorial_target = 'main'  # まだ「ごはん」「あそぶ」を押す前
    elif tutorial_step == 3:
        tutorial_target = 'rest'

    if tutorial_target:
        tutorial_text = (done_line + "\n" if done_line else "") + \
                        TUTORIAL_TEXTS[(tutorial_step, tutorial_target)]
    elif done_line:
        tutorial_text = done_line + "\n" + TUTORIAL_END_TEXT

    # ================================
    # パラメータ依存イベント
    # ================================

    if action is None and menu == '':
        character_state = "normal"
    else:
        character_state = request.session.get('character_state', 'normal')

    action_list = ['rest', 'next_day'] + PLAY_RESULT_ACTIONS + FOOD_RESULT_ACTIONS

    if action in action_list:

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
        if fullness >= 90:
            satisfaction -= 5
            growth -= 2
            character_state = "tired"

        # 満腹なのにごはん系ゲームをした
        if fullness >= 90 and action in FOOD_RESULT_ACTIONS:
            satisfaction -= 10
            energy -= 5
            character_state = "tired"

        # 元気なのに休む
        if energy >= 90 and action == 'rest':
            satisfaction -= 15
            growth -= 2
            character_state = "tired"

        # 疲れているのに遊ぶ
        if energy <= 30 and action in PLAY_RESULT_ACTIONS:
            energy -= 10
            satisfaction -= 5
            character_state = "tired"

        # 空腹なのに遊ぶ
        if fullness <= 30 and action in PLAY_RESULT_ACTIONS:
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

        # Happyならアイテム獲得チャンス（20%）
        if character_state == "happy":
            not_owned = [i for i in ALL_ITEMS if i not in items]
            if not_owned and random.randint(1, 100) <= 20:
                new_item = random.choice(not_owned)
                items.append(new_item)
                request.session['items'] = items
                new_items.append(new_item)
                item_get = True
                get_item_image = f'images/{new_item}.png'
                get_item_name = ITEM_NAMES.get(new_item, new_item)

    # -------------------------
    # 値の上限・下限
    # -------------------------

    satisfaction = max(0, min(100, satisfaction))
    energy = max(0, min(100, energy))
    growth = max(0, min(100, growth))
    fullness = max(0, min(100, fullness))
    remaining_time = max(0, remaining_time)

    # -------------------------
    # 難易度の解放チェック（成長して新しく解放されたら知らせる）
    # -------------------------

    unlock_labels = []
    new_stage = get_growth_stage(growth)

    if new_stage > notified_stage:
        for before, after in zip(
            get_difficulty_list(notified_stage),
            get_difficulty_list(new_stage),
        ):
            if after['unlocked'] and not before['unlocked']:
                unlock_labels.append(after['label'])
        notified_stage = new_stage    # 通知済みにする（二度と出さない）

    # 行動後の成長に合わせて、難易度の表示も更新する
    difficulty_list = get_difficulty_list(new_stage)

    game_end = energy <= 0 or growth >= 100
    game_status = ""
    if energy <= 0:
        game_status = "つかれて眠ってしまった…ゲームオーバー"
    elif growth >= 100:
        game_status = "大きく成長した！ゲームクリア！"

    # -------------------------
    # キャラクターのヒント・反応
    # -------------------------

    hint_type = get_hint_type(energy, fullness, satisfaction)
    hint_list = HINT_TEXTS[hint_type]

    # 悪い状態から良くなったら、うれしい反応を返す
    reaction_text = ""
    if (
        action in action_list
        and before_hint in ('hungry', 'tired', 'full', 'bored')
        and hint_type in ('normal', 'happy')
    ):
        reaction_text = random.choice(["……！", "ふふっ♪"])

    # -------------------------
    # 持ち物の表示用データ（NEW判定）
    # -------------------------

    items_display = [
        {'id': i, 'name': ITEM_NAMES.get(i, i), 'is_new': i in new_items}
        for i in items
    ]
    has_new_items = len(new_items) > 0

    # 持ち物一覧を開いたらNEWを消す
    if menu == 'items':
        new_items = []

    placed_item_images = []
    for item in placed_items:
        if item.startswith('room-'):
            continue
        pos = FURNITURE_POSITIONS.get(item, {})
        placed_item_images.append({
            'name': item,
            'image': f'images/{item}.png',
            'top': pos.get('top', 'auto'),
            'bottom': pos.get('bottom', 'auto'),
            'left': pos.get('left', 'auto'),
            'right': pos.get('right', 'auto'),
            'transform': pos.get('transform', 'none'),
            'width': pos.get('width', '120'),
        })

    # -------------------------
    # 画面に出すボタンの「押せる／押せない」
    # -------------------------

    in_tutorial = tutorial_step in (1, 2, 3)
    afford = {
        key: (in_tutorial or remaining_time >= cost)
        for key, cost in ACTION_COST.items()
    }

    # ごはん／あそぶメニューの中身
    # チュートリアル中は、指定のゲームだけ押せて、強調表示する
    forced_menu = TUTORIAL_FORCED_MENU.get(tutorial_step, '') if in_tutorial else ''

    sub_menu_items = []
    if menu in ('food', 'play'):
        for m, label, act, cost in (FOOD_MENU if menu == 'food' else PLAY_MENU):
            sub_menu_items.append({
                'menu': m, 'label': label, 'cost': cost,
                'ok': afford[act] and (not forced_menu or m == forced_menu),
                'highlight': bool(forced_menu) and m == forced_menu,
            })

    # 難易度メニュー
    difficulty_action = ''
    difficulty_cost = 0
    difficulty_affordable = False
    if menu in DIFFICULTY_MENUS:
        difficulty_action, difficulty_cost = DIFFICULTY_MENUS[menu]
        difficulty_affordable = afford[difficulty_action]

    # -------------------------
    # セッション保存
    # -------------------------

    request.session['satisfaction'] = satisfaction
    request.session['energy'] = energy
    request.session['growth'] = growth
    request.session['fullness'] = fullness
    request.session['turn'] = turn
    request.session['character_state'] = character_state
    request.session['remaining_time'] = remaining_time
    request.session['play_count'] = play_count
    request.session['healthy_food_count'] = healthy_food_count
    request.session['snack_count'] = snack_count
    request.session['tutorial_step'] = tutorial_step
    request.session['new_items'] = new_items
    request.session['notified_stage'] = notified_stage

    # -------------------------
    # 顔タイプ・性格
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
        "-active": ("げんきいっぱいタイプ",
                    "たくさん遊んで育てたため、活発で好奇心旺盛な性格に成長しました。"),
        "-gentle": ("やさしいタイプ",
                    "健康的な食事を大切にしたため、穏やかで思いやりのある性格に成長しました。"),
        "-cheerful": ("むじゃきタイプ",
                      "おやつや楽しい時間を大切にしたため、明るく人なつっこい性格に成長しました。"),
    }
    personality_name, personality_comment = personality_map.get(
        face_type,
        ("バランスタイプ", "さまざまな行動をバランスよく行ったため、なんでも器用にこなせる性格に成長しました。")
    )

    # -------------------------
    # キャラ画像・アニメーション
    # -------------------------

    growth_stage = get_growth_stage(growth)

    state_type = ""
    if growth_stage != 4:
        if character_state == "happy":
            state_type = "-happy"
        elif character_state == "tired":
            state_type = "-tired"

    character_image = f'images/character{growth_stage}{face_type}{state_type}.png'

    animation_map = {
        "happy": "happyBounce 0.8s ease-in-out infinite",
        "tired": "tiredMove 3s ease-in-out infinite",
        "hungry": "hungryShake 0.3s linear infinite",
        "full": "fullMove 4s ease-in-out infinite",
    }
    character_animation = animation_map.get(
        character_state, "floatCharacter 2s ease-in-out infinite"
    )

    # -------------------------
    # 背景・日付・時刻
    # -------------------------

    current_hour = 8 + (max_time - remaining_time)

    if current_hour < 12:
        time_zone = "morning"
    elif current_hour < 18:
        time_zone = "noon"
    else:
        time_zone = "night"

    background_image = f'images/{room_wallpaper}-{time_zone}.png'

    current_date = datetime(2026, 4, 1) + timedelta(days=turn - 1)
    date_text = f"{current_date.month}月{current_date.day}日"

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
    # 自動セーブ＋ログ記録（ここで1回だけ保存）
    # -------------------------

    if save_data is not None:

        # 総プレイ時間
        now = timezone.now()
        start_str = request.session.get('session_start')
        if start_str:
            elapsed = int((now - datetime.fromisoformat(start_str)).total_seconds())
            if 0 < elapsed < 3600:
                save_data.total_play_seconds += elapsed
        request.session['session_start'] = now.isoformat()

        # ゲームオーバー・クリア
        if energy <= 0 and before_energy > 0:
            save_data.game_over_count += 1
        if growth >= 100 and before_growth < 100:
            save_data.clear_count += 1
            if save_data.play_started_at:
                save_data.clear_time_seconds = int(
                    (now - save_data.play_started_at).total_seconds()
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
        save_data.tutorial_step = tutorial_step
        save_data.new_items = new_items
        save_data.notified_stage = notified_stage
        save_data.save()

        # 行動ログ（いつ・何をしたか）
        LOG_NAMES = {
            'ball_game': 'ボールキャッチ', 'food_result': '好きなごはん選び',
            'dodge_result': '障害物よけ', 'dance_result': 'ダンスまね',
            'timing_result': '火加減チャレンジ', 'count_result': '食材かぞえ',
            'rest': '休む', 'next_day': '次の日へ',
        }
        if action in LOG_NAMES:
            if action == 'ball_game':
                result_str = f"スコア:{get_int(request, 'score')}"
            elif action == 'dodge_result':
                result_str = f"ライフ:{get_int(request, 'lives')} スコア:{get_int(request, 'score')}"
            elif action in ('food_result', 'timing_result', 'count_result'):
                result_str = f"ライフ:{get_int(request, 'lives')}"
            elif action == 'dance_result':
                result_str = request.GET.get('result', 'fail')
            else:
                result_str = ''

            # チュートリアル中の行動には印をつける（分析で除外できるように）
            if was_tutorial:
                result_str = (result_str + ' [練習]').strip()

            ActionLog.objects.create(
                user=request.user, action=LOG_NAMES[action], turn=turn,
                energy=energy, fullness=fullness, satisfaction=satisfaction,
                growth=growth, result=result_str,
            )

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
        'menu': menu,
        'remaining_time': remaining_time,
        'personality_name': personality_name,
        'personality_comment': personality_comment,
        'date_text': date_text,
        'time_text': time_text,
        'difficulty_list': difficulty_list,
        'item_get': item_get,
        'get_item_image': get_item_image,
        'get_item_name': get_item_name,
        'items': items,
        'items_display': items_display,
        'has_new_items': has_new_items,
        'owned_count': owned_count,
        'total_count': total_count,
        'collection_rate': collection_rate,
        'placed_items': placed_items,
        'placed_item_images': placed_item_images,
        'room_wallpaper': background_image,
        'background_image': background_image,
        'sleep_hours': remaining_time,
        'character_damage_image': f"images/character{growth_stage}-tired.png",
        'tutorial_step': tutorial_step,
        'tutorial_text': tutorial_text,
        'tutorial_choice_required': request.session.get('tutorial_choice_required', False),
        'in_tutorial': in_tutorial,
        'afford': afford,
        'sub_menu_items': sub_menu_items,
        'difficulty_action': difficulty_action,
        'difficulty_cost': difficulty_cost,
        'difficulty_affordable': difficulty_affordable,
        'hint_list': hint_list,
        'initial_speech': reaction_text,
        'tutorial_target': tutorial_target,
        'unlock_labels': unlock_labels,
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
        "character_damage_image": f"images/character{growth_stage}-tired.png",
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
        'easy': {'round_count': 3, 'speed': 1.0, 'zone_width': 28},
        'normal': {'round_count': 4, 'speed': 1.5, 'zone_width': 22},
        'hard': {'round_count': 5, 'speed': 2.0, 'zone_width': 17},
        'oni': {'round_count': 6, 'speed': 2.8, 'zone_width': 13},
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