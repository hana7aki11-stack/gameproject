from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.urls import reverse
from urllib.parse import urlencode
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db import transaction
from django.utils import timezone

from .models import (
    RealTimeSaveData,
    RealTimeMinigameSession,
    RealTimeActionLog,
)

from .time_system import (
    apply_elapsed_time,
    is_sleep_time,
    is_sitter_time,
    change_bedtime,
    start_sitter,
    end_sitter,
)

from .action_system import (
    get_growth_stage,
    apply_action,
    ITEM_NAMES,
    ALL_ITEMS,
)
from .round_system import start_new_round

from .minigame_system import (
    start_minigame,
    finish_minigame,
    abandon_minigame,
)
from datetime import timedelta, datetime, time
from django.utils.dateparse import parse_datetime
import math

from play_session_system import (
    touch_play_session,
    close_play_session,
)

from .models import RealTimePlaySession

# =========================
# チュートリアルのセリフ
# =========================

TUTORIAL_TEXTS = {
    (1, 'main'): "STEP 1　ごはん\nおなかがすいているみたいです。\n「ごはん」を押してね。",
    (1, 'submenu'): "STEP 1　ごはん\nまずは「好きなごはん選び」を選んでみよう！",
    (1, 'level'): "STEP 1　ごはん\nむずかしさは「かんたん」を選んでね。",

    (2, 'main'): "STEP 2　あそぶ\n元気があるときは、一緒に遊んでみましょう！\n「あそぶ」を押してね。",
    (2, 'submenu'): "STEP 2　あそぶ\nまずは「ダンスまね」を選んでみよう！",
    (2, 'level'): "STEP 2　あそぶ\nむずかしさは「かんたん」を選んでね。",

    (3, 'rest'): "STEP 3　休む\n疲れたときは休ませてあげましょう。\n「休む」を押してみてね。",
}

TUTORIAL_DONE_LINES = {
    1: "✓ おなかいっぱいになりました！",
    2: "✓ 上手に遊べました！",
    3: "✓ ゆっくり休んで元気になりました！",
}

TUTORIAL_END_TEXT = "チュートリアル完了！\nここからは、この子の様子をよく見ながら育ててみてね。"

# =========================
# 家具の種類
# =========================

ITEM_CATEGORIES = {
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


# =========================
# 家具の配置位置・サイズ
# =========================

FURNITURE_POSITIONS = {

    # ソファ
    'sofa': {
        'bottom': '20px',
        'left': '30px',
        'width': '240',
    },

    'sofa-star': {
        'bottom': '40px',
        'left': '30px',
        'width': '240',
    },

    'sofa-kawaii': {
        'bottom': '50px',
        'left': '30px',
        'width': '240',
    },

    # 観葉植物
    'plant': {
        'bottom': '20px',
        'right': '-40px',
        'width': '280',
    },

    'plant-star': {
        'bottom': '20px',
        'right': '-100px',
        'width': '400',
    },

    'plant-kawaii': {
        'bottom': '20px',
        'right': '-40px',
        'width': '280',
    },

    # ラグ
    'rug': {
        'bottom': '0px',
        'left': '50%',
        'transform': 'translateX(-50%)',
        'width': '160',
    },

    'rug-star': {
        'bottom': '-10px',
        'left': '50%',
        'transform': 'translateX(-50%)',
        'width': '250',
    },

    'rug-kawaii': {
        'bottom': '-5px',
        'left': '50%',
        'transform': 'translateX(-50%)',
        'width': '160',
    },

    # 時計
    'clock': {
        'top': '20px',
        'right': '170px',
        'width': '100',
    },

    'clock-star': {
        'top': '20px',
        'right': '170px',
        'width': '100',
    },

    'clock-kawaii': {
        'top': '20px',
        'right': '170px',
        'width': '100',
    },
}

# =========================
# 難易度設定
# =========================

# =========================
# ボールキャッチ
# =========================

BALL_DIFFICULTY_SETTINGS = {
    "easy": {
        "ball_speed": 1.0,
        "spawn_interval": 1000,
        "score_multiplier": 1,
    },
    "normal": {
        "ball_speed": 1.4,
        "spawn_interval": 800,
        "score_multiplier": 1,
    },
    "hard": {
        "ball_speed": 1.8,
        "spawn_interval": 600,
        "score_multiplier": 1,
    },
    "oni": {
        "ball_speed": 2.4,
        "spawn_interval": 400,
        "score_multiplier": 1,
    },
}


# =========================
# 好きなごはん選び
# =========================

FOOD_DIFFICULTY_SETTINGS = {
    "easy": {
        "flow_speed": 1.0,
        "spawn_interval": 1200,
        "time_limit": 20,
        "score_multiplier": 1,
    },
    "normal": {
        "flow_speed": 1.4,
        "spawn_interval": 900,
        "time_limit": 18,
        "score_multiplier": 1.5,
    },
    "hard": {
        "flow_speed": 1.8,
        "spawn_interval": 700,
        "time_limit": 15,
        "score_multiplier": 2,
    },
    "oni": {
        "flow_speed": 2.2,
        "spawn_interval": 600,
        "time_limit": 12,
        "score_multiplier": 3,
    },
}


# =========================
# 火加減チャレンジ
# =========================

TIMING_DIFFICULTY_SETTINGS = {
    "easy": {
        "round_count": 3,
        "speed": 1.0,
        "zone_width": 28,
    },
    "normal": {
        "round_count": 4,
        "speed": 1.5,
        "zone_width": 22,
    },
    "hard": {
        "round_count": 5,
        "speed": 2.0,
        "zone_width": 17,
    },
    "oni": {
        "round_count": 6,
        "speed": 2.8,
        "zone_width": 13,
    },
}


# =========================
# 食材かぞえ
# =========================

COUNT_DIFFICULTY_SETTINGS = {
    "easy": {
        "round_count": 3,
        "display_time": 3000,
        "item_count": 6,
        "type_count": 2,
    },
    "normal": {
        "round_count": 4,
        "display_time": 2500,
        "item_count": 9,
        "type_count": 3,
    },
    "hard": {
        "round_count": 5,
        "display_time": 2000,
        "item_count": 12,
        "type_count": 4,
    },
    "oni": {
        "round_count": 6,
        "display_time": 1500,
        "item_count": 15,
        "type_count": 5,
    },
}


# =========================
# 障害物よけ
# =========================

DODGE_DIFFICULTY_SETTINGS = {
    "easy": {
        "obstacle_count": 2,
        "fall_speed": 1.0,
        "time_limit": 20,
    },
    "normal": {
        "obstacle_count": 3,
        "fall_speed": 1.4,
        "time_limit": 18,
    },
    "hard": {
        "obstacle_count": 4,
        "fall_speed": 1.8,
        "time_limit": 15,
    },
    "oni": {
        "obstacle_count": 5,
        "fall_speed": 2.4,
        "time_limit": 12,
    },
}


# =========================
# ダンスまね
# =========================

DANCE_DIFFICULTY_SETTINGS = {
    "easy": {
        "sequence_length": 3,
        "show_seconds": 4,
    },
    "normal": {
        "sequence_length": 4,
        "show_seconds": 5,
    },
    "hard": {
        "sequence_length": 5,
        "show_seconds": 6,
    },
    "oni": {
        "sequence_length": 7,
        "show_seconds": 8,
    },
}


# =========================
# ミニゲーム共通設定
# =========================

MINIGAME_CONFIG = {

    "ball": {
        "title": "ボールキャッチ",
        "settings": BALL_DIFFICULTY_SETTINGS,
        "extra": {
            "ball_image": "images/ball.png",
        },
    },

    "food": {
        "title": "好きなごはん選び",
        "settings": FOOD_DIFFICULTY_SETTINGS,
        "extra": {
            "food_item_images": [
                "images/food1.png",
                "images/food2.png",
                "images/food3.png",
                "images/food4.png",
                "images/food5.png",
                "images/food6.png",
            ],
        },
    },

    "timing": {
        "title": "火加減チャレンジ",
        "settings": TIMING_DIFFICULTY_SETTINGS,
        "extra": {},
    },

    "count": {
        "title": "食材かぞえ",
        "settings": COUNT_DIFFICULTY_SETTINGS,
        "extra": {
            "food_emojis": [
                "🍎", "🍌", "🍇", "🍓",
                "🥕", "🌽", "🍳", "🥚",
                "🧀", "🍗",
            ],
        },
    },

    "dodge": {
        "title": "障害物よけ",
        "settings": DODGE_DIFFICULTY_SETTINGS,
        "extra": {},
    },

    "dance": {
        "title": "ダンスまね",
        "settings": DANCE_DIFFICULTY_SETTINGS,
        "extra": {},
    },

}



# =========================
# 育成データの取得
# =========================

def get_save_data(request):

    save_data, created = (
        RealTimeSaveData.objects.get_or_create(
            user=request.user
        )
    )

    return save_data


# =========================
# ホーム画面
# =========================

# キャラクターのセリフ
# 状態を直接説明せず、プレイヤーに推測してもらう
HINT_TEXTS = {
    'hungry': ["なんだかそわそわするな……"],
    'tired':  ["なんだか元気が出ないな……"],
    'full':   ["うぅ……"],
    'bored':  ["ねえねえ……"],
    'happy':  ["ふふっ♪"],
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

@login_required
@never_cache
def home(request):

    save_data = get_save_data(request)

    save_data = apply_elapsed_time(
        save_data
    )

    # =========================
    # プレイ中のミニゲームを確認
    # =========================

    active_minigame = (
        RealTimeMinigameSession.objects.filter(
            user=request.user,
            game_round=save_data.game_round,
            status="playing",
            started_at__gt=(
                timezone.now() - timedelta(minutes=15)
            )
        ).first()
    )

    current_time = timezone.localtime()

    # =========================
    # 起床時刻の計算
    # =========================

    wakeup_time = (
        datetime.combine(
            current_time.date(),
            save_data.bedtime
        )
        + timedelta(hours=8)
    ).time()

    # 選択可能な就寝時刻
    bedtime_options = [
        f"{hour:02d}:00"
        for hour in range(24)
    ]

    # =========================
    # 休むストックの回復時間
    # =========================

    rest_recovery_minutes = None

    rest_recovery_text = (
        save_data.stock_recovery_at.get("rest")
    )

    if save_data.stock_rest < 2 and rest_recovery_text:

        recovery_at = parse_datetime(
            rest_recovery_text
        )

        if recovery_at is not None:

            if timezone.is_naive(recovery_at):
                recovery_at = timezone.make_aware(
                    recovery_at
                )

            remaining_seconds = max(
                0,
                (
                    recovery_at - current_time
                ).total_seconds()
            )

            rest_recovery_minutes = math.ceil(
                remaining_seconds / 60
            )

    growth_stage = get_growth_stage(save_data.growth)

    playing = save_data.status == "playing"

    # イントロ・チュートリアル・追加説明中かどうか
    in_tutorial = (
            playing and save_data.tutorial_step != 4
    )

    # リアルタイム型の追加説明中かどうか
    in_extra_intro = (
            playing and save_data.tutorial_step == 5
    )
    # チュートリアルを最後まで行ったか確認
    show_tutorial_complete = False

    if in_extra_intro:

        tutorial_skipped = (
            RealTimeActionLog.objects.filter(
                user=request.user,
                game_round=save_data.game_round,
                action="tutorial_skip",
            ).exists()
        )

        show_tutorial_complete = not tutorial_skipped

    # チュートリアル中は睡眠・シッターを適用しない
    sleeping = (
            playing
            and not in_tutorial
            and is_sleep_time(
        current_time,
        save_data.bedtime
    )
    )

    sitting = (
            playing
            and not in_tutorial
            and is_sitter_time(
        save_data,
        current_time
    )
    )

    blocked = (
            not playing
            or sleeping
            or sitting
            or in_extra_intro
            or bool(active_minigame)
    )

    # =========================
    # シッターの利用状況
    # =========================

    # 本日すでに利用しているか
    sitter_used_today = (
        save_data.sitter_last_used_date
        == current_time.date()
    )

    # シッターの利用可能時間
    sitter_business_hours = (
        time(6, 0)
        <= current_time.time()
        < time(19, 0)
    )

    # シッターに預けられるか
    can_use_sitter = (
            playing
            and not in_tutorial
            and not sitting
            and not sitter_used_today
            and sitter_business_hours
            and not active_minigame
    )

    difficulty_list = [
        {"key": key, "label": label, "unlocked": i <= growth_stage}
        for i, (key, label) in enumerate([
            ("easy", "かんたん"), ("normal", "ふつう"),
            ("hard", "むずかしい"), ("oni", "鬼")
        ])
    ]
    groups = {"food": ("food", "timing", "count"),
              "play": ("dance", "ball", "dodge")}
    menu = request.GET.get("menu", "")
    selected = request.GET.get("game", "")
    minigames = []

    if menu in groups:

        for action in groups[menu]:

            # 現在のストック
            stock = getattr(
                save_data,
                f"stock_{action}"
            )

            # 次回回復までの残り時間
            recovery_minutes = None

            recovery_text = (
                save_data.stock_recovery_at.get(action)
            )

            if stock < 2 and recovery_text:

                recovery_at = parse_datetime(
                    recovery_text
                )

                if recovery_at is not None:

                    if timezone.is_naive(recovery_at):
                        recovery_at = timezone.make_aware(
                            recovery_at
                        )

                    remaining_seconds = max(
                        0,
                        (
                                recovery_at - current_time
                        ).total_seconds()
                    )

                    recovery_minutes = math.ceil(
                        remaining_seconds / 60
                    )

            minigames.append({
                "action": action,
                "title": MINIGAME_CONFIG[action]["title"],
                "url_name": f"real_time_game:{action}_game",
                "stock": stock,
                "recovery_minutes": recovery_minutes,
            })
    selected_game = next((g for g in minigames if g["action"] == selected), None)

    # =========================
    # チュートリアルの案内文
    # =========================

    tutorial_text = ""
    tutorial_step = save_data.tutorial_step

    tutorial_done_lines = []

    if in_tutorial and tutorial_step in (2, 3):

        tutorial_done_lines = [
            TUTORIAL_DONE_LINES[tutorial_step - 1]
        ]

    if in_tutorial:

        if tutorial_step == 1:

            if menu == "food" and selected == "food":
                position = "level"

            elif menu == "food":
                position = "submenu"

            else:
                position = "main"

            tutorial_text = TUTORIAL_TEXTS[(1, position)]

        elif tutorial_step == 2:

            if menu == "play" and selected == "dance":
                position = "level"

            elif menu == "play":
                position = "submenu"

            else:
                position = "main"

            tutorial_text = TUTORIAL_TEXTS[(2, position)]

        elif tutorial_step == 3:

            tutorial_text = TUTORIAL_TEXTS[(3, "rest")]

    energy, fullness, satisfaction = save_data.energy, save_data.fullness, save_data.satisfaction
    play_count = save_data.play_count
    healthy_food_count = save_data.healthy_food_count
    snack_count = save_data.snack_count
    if play_count >= healthy_food_count + 3 and play_count >= snack_count + 3:
        face_type = "-active"
    elif healthy_food_count >= play_count + 3 and healthy_food_count >= snack_count + 3:
        face_type = "-gentle"
    elif snack_count >= play_count + 3 and snack_count >= healthy_food_count + 3:
        face_type = "-cheerful"
    else:
        face_type = ""

    hint_type = get_hint_type(energy, fullness, satisfaction)

    # 行動直後だけ、保存されたリアクションを表示する
    # それ以外はターン制と同様に通常の表情に戻す
    character_state = request.session.pop(
        "rt_character_reaction",
        "normal"
    )

    if character_state not in ("normal", "happy", "tired"):
        character_state = "normal"

    # ================================
    # 画面表示専用のキャラクター状態
    # tiredをhappyより優先する
    # ================================

    is_tired = (
            satisfaction <= 30
            or energy <= 30
            or fullness <= 30
            or fullness >= 90
            or character_state == "tired"
    )

    if is_tired:
        display_character_state = "tired"
    elif character_state == "happy" or satisfaction >= 80:
        display_character_state = "happy"
    else:
        display_character_state = "normal"

    state_type = ""
    if growth_stage != 4 and display_character_state in ("happy", "tired"):
        state_type = "-" + display_character_state
    character_image = f"images/character{growth_stage}{face_type}{state_type}.png"
    animation_map = {
        "happy": "happyBounce 0.8s ease-in-out infinite",
        "tired": "tiredMove 3s ease-in-out infinite",
    }
    hour = current_time.hour

    # =========================
    # キャラクターの演出
    # =========================

    character_animation = animation_map.get(
        display_character_state,
        "floatCharacter 2s ease-in-out infinite"
    )

    hint_list = HINT_TEXTS[hint_type]

    # 睡眠中の演出
    if sleeping:
        # 睡眠中は性格に関係なく、
        # 成長段階ごとの共通画像を使用
        character_image = (
            f"images/character{growth_stage}-sleep.png"
        )

        character_animation = (
            "sleepCharacter 4s ease-in-out infinite"
        )

        hint_list = [
            "すやすや……",
            "むにゃむにゃ……"
        ]

    time_zone = "morning" if hour < 12 else "noon" if hour < 18 else "night"
    # =========================
    # 持ち物一覧の表示
    # =========================

    items = [
        item for item in save_data.items
        if item in ALL_ITEMS
    ]

    placed_items = save_data.placed_items
    new_items = save_data.new_items

    items_display = []

    for item in items:

        is_wallpaper = item.startswith("room-")

        items_display.append({

            "id": item,

            "name": ITEM_NAMES.get(item, item),

            "image": f"images/{item}.png",

            "is_new": item in new_items,

            "is_wallpaper": is_wallpaper,

            "is_placed": item in placed_items,

            "is_selected": (
                is_wallpaper
                and item == save_data.room_wallpaper
            ),

        })

    has_new_items = bool(new_items)

    # アイテムの収集率
    owned_count = len(set(items))
    total_count = len(ALL_ITEMS)

    collection_rate = round(
        owned_count / total_count * 100
    ) if total_count else 0


    # =========================
    # 部屋に配置する家具
    # =========================

    placed_item_images = []

    for item in placed_items:

        if item not in items:
            continue

        if item not in FURNITURE_POSITIONS:
            continue

        pos = FURNITURE_POSITIONS[item]

        placed_item_images.append({

            "name": ITEM_NAMES.get(item, item),

            "image": f"images/{item}.png",

            "top": pos.get("top", "auto"),

            "bottom": pos.get("bottom", "auto"),

            "left": pos.get("left", "auto"),

            "right": pos.get("right", "auto"),

            "transform": pos.get("transform", "none"),

            "width": pos.get("width", "120"),

        })
    context = {
        "save_data": save_data, "current_time": current_time,

        "in_tutorial": in_tutorial,
        "in_extra_intro": in_extra_intro,
        "show_tutorial_complete": show_tutorial_complete,
        "tutorial_text": tutorial_text,
        "tutorial_end_text": TUTORIAL_END_TEXT,
        "tutorial_done_lines": tutorial_done_lines,

        "rest_recovery_minutes": rest_recovery_minutes,
        "active_minigame": active_minigame, "blocked": blocked,
        "sleeping": sleeping, "sitting": sitting,
        "sitter_used_today": sitter_used_today,
        "sitter_business_hours": sitter_business_hours,
        "can_use_sitter": can_use_sitter,
        "minigames": minigames, "selected_game": selected_game,
        "difficulty_list": difficulty_list, "menu": menu,
        "energy": energy, "fullness": fullness, "satisfaction": satisfaction,
        "character_image": character_image,
        "character_animation": character_animation,
        "background_image": f"images/{save_data.room_wallpaper}-{time_zone}.png",
                "hint_list": hint_list,

        "wakeup_time": wakeup_time,
        "bedtime_options": bedtime_options,
        # 家具・持ち物関連
        "items_display": items_display,
        "placed_items": placed_items,
        "placed_item_images": placed_item_images,
        "has_new_items": has_new_items,
        "owned_count": owned_count,
        "total_count": total_count,
        "collection_rate": collection_rate,
    }

    # =========================
    # 自動更新時の処理
    # =========================

    if request.headers.get("X-Game-Auto-Refresh") == "1":
        # 自動更新では操作結果のメッセージを消費しない
        context["messages"] = []

    return render(
        request,
        "real_time_game/home.html",
        context
    )


# =========================
# 育成開始（動作確認用）
# =========================

@login_required
@require_POST
@transaction.atomic
def start_test_game(request):

    save_data = get_save_data(request)

    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    if save_data.status != "not_started":

        messages.error(
            request,
            "すでに育成が開始されています"
        )

        return redirect("real_time_game:home")

    now = timezone.now()

    save_data.status = "playing"
    save_data.has_started_game = True

    save_data.play_started_at = now
    save_data.last_updated_at = now

    # イントロから育成を開始する
    save_data.tutorial_step = 0

    save_data.save()

    return redirect("real_time_game:home")


# =========================
# イントロの終了
# =========================

@login_required
@require_POST
@transaction.atomic
def finish_intro(request):

    save_data = get_save_data(request)

    # 同時操作によるデータの不整合を防止
    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    # 現在の育成回数を確認
    try:
        expected_round = int(
            request.POST.get("game_round", "")
        )
    except (TypeError, ValueError):
        return redirect("real_time_game:home")

    if save_data.game_round != expected_round:
        return redirect("real_time_game:home")

    # イントロ中のみ実行可能
    if (
        save_data.status != "playing"
        or save_data.tutorial_step != 0
    ):
        return redirect("real_time_game:home")

    now = timezone.now()

    # ごはんのチュートリアルへ進む
    save_data.tutorial_step = 1

    # お腹が空いている状態にする
    save_data.fullness = 25

    # 時間経過による変動を防止
    save_data.last_updated_at = now

    save_data.save(
        update_fields=[
            "tutorial_step",
            "fullness",
            "last_updated_at",
        ]
    )

    # 研究用ログ
    RealTimeActionLog.objects.create(
        user=request.user,
        game_round=save_data.game_round,
        action="intro_finish",
        timestamp=now,
        satisfaction=save_data.satisfaction,
        energy=save_data.energy,
        fullness=save_data.fullness,
        growth=save_data.growth,
        result="イントロ終了",
    )

    return redirect("real_time_game:home")

# =========================
# チュートリアルのスキップ
# =========================

@login_required
@require_POST
@transaction.atomic
def skip_tutorial(request):

    save_data = get_save_data(request)

    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    # 現在の育成回数を確認
    try:
        expected_round = int(
            request.POST.get("game_round", "")
        )
    except (TypeError, ValueError):
        return redirect("real_time_game:home")

    if save_data.game_round != expected_round:
        return redirect("real_time_game:home")

    # チュートリアル中のみ実行可能
    if (
        save_data.status != "playing"
        or save_data.tutorial_step not in (1, 2, 3)
    ):
        return redirect("real_time_game:home")

    now = timezone.now()

    # ミニゲーム中はスキップできない
    active_minigame = (
        RealTimeMinigameSession.objects.filter(
            user=request.user,
            game_round=save_data.game_round,
            status="playing",
            started_at__gt=(
                now - timedelta(minutes=15)
            )
        ).exists()
    )

    if active_minigame:

        messages.error(
            request,
            "ミニゲーム終了後にスキップできます"
        )

        return redirect("real_time_game:home")

    # スキップ前のSTEPを記録
    previous_step = save_data.tutorial_step

    # リアルタイム型の追加説明へ移行する
    save_data.tutorial_step = 5
    save_data.last_updated_at = now

    save_data.save(
        update_fields=[
            "tutorial_step",
            "last_updated_at",
        ]
    )

    # 研究用ログ
    RealTimeActionLog.objects.create(
        user=request.user,
        game_round=save_data.game_round,
        action="tutorial_skip",
        timestamp=now,
        satisfaction=save_data.satisfaction,
        energy=save_data.energy,
        fullness=save_data.fullness,
        growth=save_data.growth,
        result=f"STEP{previous_step}でスキップ",
    )

    messages.success(
        request,
        "チュートリアルを終了しました"
    )

    return redirect("real_time_game:home")

# =========================
# リアルタイム型の追加説明終了
# =========================

@login_required
@require_POST
@transaction.atomic
def finish_extra_intro(request):

    save_data = get_save_data(request)

    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    # 育成回の確認
    try:
        expected_round = int(
            request.POST.get("game_round", "")
        )

    except (TypeError, ValueError):
        return redirect("real_time_game:home")

    if save_data.game_round != expected_round:
        return redirect("real_time_game:home")

    # 追加説明中のみ終了できる
    if (
        save_data.status != "playing"
        or save_data.tutorial_step != 5
    ):
        return redirect("real_time_game:home")

    now = timezone.now()

    # 通常育成を開始する
    save_data.tutorial_step = 4
    save_data.last_updated_at = now

    save_data.save(
        update_fields=[
            "tutorial_step",
            "last_updated_at",
        ]
    )

    # 研究用ログ
    RealTimeActionLog.objects.create(
        user=request.user,
        game_round=save_data.game_round,
        action="extra_intro_finish",
        timestamp=now,
        satisfaction=save_data.satisfaction,
        energy=save_data.energy,
        fullness=save_data.fullness,
        growth=save_data.growth,
        result="追加説明終了",
    )

    return redirect("real_time_game:home")

# =========================
# ミニゲーム共通開始処理
# =========================

def render_minigame(request, action):

    save_data = get_save_data(request)

    difficulty = request.POST.get(
        "difficulty", "easy"
    )

    # ストック消費・開始記録
    save_data, success, info = start_minigame(
        save_data,
        action,
        difficulty=difficulty
    )

    if not success:

        messages.error(
            request,
            info["message"]
        )

        return redirect("real_time_game:home")

    # 現在の成長段階
    growth_stage = get_growth_stage(
        save_data.growth
    )

    # 開始時に確定した難易度
    selected_difficulty = info["difficulty"]

    # ミニゲームごとの設定
    game_config = MINIGAME_CONFIG[action]

    current_settings = game_config[
        "settings"
    ][selected_difficulty]

    # 全ミニゲームで使用する共通データ
    context = {

        "game_round": save_data.game_round,

        "growth_stage": growth_stage,

        "character_image":
            f"images/character{growth_stage}.png",

        "character_happy_image":
            f"images/character{growth_stage}-happy.png",

        "character_damage_image":
            f"images/character{growth_stage}-tired.png",

        "background_image":
            "images/morning.png",

        "game_title":
            game_config["title"],

        "selected_difficulty":
            selected_difficulty,

        "minigame_token":
            info["token"],

    }

    # 難易度ごとの設定を追加
    context.update(current_settings)

    # ミニゲーム固有の画像などを追加
    context.update(game_config["extra"])

    return render(
        request,
        f"real_time_game/{action}_game.html",
        context
    )


# =========================
# ボールキャッチ
# =========================

@login_required
@require_POST
def ball_game(request):

    return render_minigame(
        request, "ball"
    )


# =========================
# 好きなごはん選び
# =========================

@login_required
@require_POST
def food_game(request):

    return render_minigame(
        request, "food"
    )


# =========================
# 火加減チャレンジ
# =========================

@login_required
@require_POST
def timing_game(request):

    return render_minigame(
        request, "timing"
    )


# =========================
# 食材かぞえ
# =========================

@login_required
@require_POST
def count_game(request):

    return render_minigame(
        request, "count"
    )


# =========================
# 障害物よけ
# =========================

@login_required
@require_POST
def dodge_game(request):

    return render_minigame(
        request, "dodge"
    )


# =========================
# ダンスまね
# =========================

@login_required
@require_POST
def dance_game(request):

    return render_minigame(
        request, "dance"
    )



# =========================
# ミニゲーム結果の受け取り
# =========================

@login_required
@require_POST
def minigame_result(request):

    save_data = get_save_data(request)

    token = request.POST.get("token", "")

    try:

        score = int(
            request.POST.get("score", 0)
        )

        lives = int(
            request.POST.get("lives", 0)
        )

    except (TypeError, ValueError):

        messages.error(
            request,
            "無効なゲーム結果です"
        )

        return redirect("real_time_game:home")

    result = request.POST.get(
        "result", "fail"
    )

    # 異常な入力値を拒否
    if (
        not 0 <= score <= 10000
        or not 0 <= lives <= 3
        or result not in ("clear", "fail")
    ):

        messages.error(
            request,
            "無効なゲーム結果です"
        )

        return redirect("real_time_game:home")

    save_data, success, info = finish_minigame(
        save_data,
        token,
        score=score,
        lives=lives,
        result=result
    )

    if success:

        # ミニゲーム終了直後の表情を1回だけ表示
        request.session["rt_character_reaction"] = (
            save_data.character_state
        )

        messages.success(
            request,
            info["message"],
            extra_tags="character_event"
        )

        for message in info["event_messages"]:
            messages.info(
                request,
                message,
                extra_tags="character_event"
            )

        if info["new_item"]:
            messages.success(
                request,
                info["new_item"],
                extra_tags="item_get"
            )

    else:

        messages.error(
            request,
            info["message"]
        )

    return redirect("real_time_game:home")


# =========================
# ミニゲームの途中離脱
# =========================

@login_required
@require_POST
def minigame_abandon(request):

    save_data = get_save_data(request)

    token = request.POST.get("token", "")

    save_data, success, info = abandon_minigame(
        save_data,
        token
    )

    if success:

        messages.info(
            request,
            info["message"]
        )

    else:

        messages.error(
            request,
            info["message"]
        )

    return redirect("real_time_game:home")

# =========================
# 休む
# =========================

@login_required
@require_POST
@transaction.atomic
def rest(request):

    save_data = get_save_data(request)

    # 同時操作によるデータの不整合を防止
    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    now = timezone.now()

    # ミニゲーム中は休むことができない
    active_minigame = (
        RealTimeMinigameSession.objects.filter(
            user=request.user,
            game_round=save_data.game_round,
            status="playing",
            started_at__gt=(
                now - timedelta(minutes=15)
            )
        ).exists()
    )

    if active_minigame:

        messages.error(
            request,
            "ミニゲーム中は休むことができません"
        )

        return redirect("real_time_game:home")

    # 行動前のチュートリアル状態を記録
    was_tutorial = save_data.tutorial_step == 3

    # 既存の行動処理を利用
    save_data, success, info = apply_action(
        save_data,
        "rest",
        now=now
    )

    # 家具を獲得した場合
    if success and info["new_item"]:
        messages.success(
            request,
            info["new_item"],
            extra_tags="item_get"
        )

    # チュートリアル完了後は追加説明へ移行
    if (
            success
            and was_tutorial
            and save_data.tutorial_step == 5
    ):
        return redirect("real_time_game:home")

    if success:

        # 休んだ直後の表情を1回だけ表示
        request.session["rt_character_reaction"] = (
            save_data.character_state
        )

        # キャラクターの頭上にコメントを表示
        messages.success(
            request,
            info["message"],
            extra_tags="character_event"
        )

        # 追加イベントの表示
        for message in info["event_messages"]:

            messages.info(
                request,
                message,
                extra_tags="character_event"
            )



    else:

        messages.error(
            request,
            info["message"]
        )

    return redirect("real_time_game:home")

# =========================
# 新しい育成を開始
# =========================

@login_required
@require_POST
def new_round(request):

    save_data = get_save_data(request)

    # 現在の育成回数を受け取る
    try:

        expected_round = int(
            request.POST.get("game_round", "")
        )

    except (TypeError, ValueError):

        messages.error(
            request,
            "無効な操作です"
        )

        return redirect("real_time_game:home")

    # 新しい育成を開始する
    save_data, success, message = start_new_round(
        save_data,
        expected_round
    )

    if success:

        messages.success(
            request,
            message,
            extra_tags="character_event"
        )

    else:

        messages.error(
            request,
            message
        )

    return redirect("real_time_game:home")

# =========================
# ゲームのリセット
# =========================

@login_required
@require_POST
def reset_game(request):

    save_data = get_save_data(request)

    # 現在の育成回数を受け取る
    try:

        expected_round = int(
            request.POST.get("game_round", "")
        )

    except (TypeError, ValueError):

        messages.error(
            request,
            "無効な操作です"
        )

        return redirect("real_time_game:home")

    # リセット処理を実行
    save_data, success, message = start_new_round(
        save_data,
        expected_round,
        reset=True
    )

    if success:

        messages.success(
            request,
            message
        )

    else:

        messages.error(
            request,
            message
        )

    return redirect("real_time_game:home")

# =========================
# ログアウト
# =========================

@login_required
@require_POST
def logout_game(request):
    save_data = get_save_data(request)

    # ログアウトする時点までのプレイ時間を記録
    close_play_session(
        user=request.user,
        save_model=RealTimeSaveData,
        session_model=RealTimePlaySession,
        is_logout=True,
    )

    # 最新の保存データを取得
    save_data.refresh_from_db()

    # ログアウトする時点までの時間経過を反映
    save_data = apply_elapsed_time(
        save_data
    )

    # ログアウト
    logout(request)

    # 再ログイン後の移動先
    next_url = reverse("real_time_game:home")

    login_url = reverse("login")

    query = urlencode({
        "next": next_url
    })

    return redirect(
        f"{login_url}?{query}"
    )

# =========================
# 就寝時刻の変更
# =========================

@login_required
@require_POST
@transaction.atomic
def set_bedtime(request):

    save_data = get_save_data(request)

    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    now = timezone.now()

    # 入力された就寝時刻
    bedtime_text = request.POST.get(
        "bedtime", ""
    )

    # 1時間単位の入力のみ許可
    valid_options = [
        f"{hour:02d}:00"
        for hour in range(24)
    ]

    if bedtime_text not in valid_options:

        messages.error(
            request,
            "正しい就寝時刻を選択してください"
        )

        return redirect("real_time_game:home")

    new_bedtime = time(
        int(bedtime_text[:2]),
        0
    )

    # 現在までの時間経過を反映
    save_data = apply_elapsed_time(
        save_data,
        now=now
    )

    # 育成中のみ変更可能
    if save_data.status != "playing":

        messages.error(
            request,
            "育成中のみ就寝時刻を変更できます"
        )

        return redirect("real_time_game:home")

    # イントロ・チュートリアル中は変更不可
    if save_data.tutorial_step != 4:

        messages.error(
            request,
            "チュートリアル終了後に就寝時刻を変更できます"
        )

        return redirect("real_time_game:home")

    # ミニゲーム中は変更不可
    active_minigame = (
        RealTimeMinigameSession.objects.filter(
            user=request.user,
            game_round=save_data.game_round,
            status="playing",
            started_at__gt=(
                now - timedelta(minutes=15)
            )
        ).exists()
    )

    if active_minigame:

        messages.error(
            request,
            "ミニゲーム中は就寝時刻を変更できません"
        )

        return redirect("real_time_game:home")

    # 同じ時刻の場合
    if save_data.bedtime == new_bedtime:

        messages.info(
            request,
            "現在と同じ就寝時刻です"
        )

        return redirect("real_time_game:home")

    # 既存の就寝時刻変更処理を利用
    save_data = change_bedtime(
        save_data,
        new_bedtime,
        now=now
    )

    messages.success(
        request,
        f"就寝時刻を{new_bedtime:%H:%M}に変更しました！"
    )

    return redirect("real_time_game:home")


# =========================
# シッターに預ける
# =========================

@login_required
@require_POST
@transaction.atomic
def deposit_sitter(request):

    save_data = get_save_data(request)

    # 同時操作によるデータの不整合を防止
    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    now = timezone.now()

    # ミニゲーム中は預けられない
    active_minigame = (
        RealTimeMinigameSession.objects.filter(
            user=request.user,
            game_round=save_data.game_round,
            status="playing",
            started_at__gt=(
                now - timedelta(minutes=15)
            )
        ).exists()
    )

    if active_minigame:

        messages.error(
            request,
            "ミニゲーム中はシッターを利用できません"
        )

        return redirect("real_time_game:home")

    # 既存のシッター開始処理を利用
    save_data, success, message = start_sitter(
        save_data,
        now=now
    )

    if success:

        messages.success(
            request,
            "シッターに預けました！"
        )

    else:

        messages.error(
            request,
            message
        )

    return redirect("real_time_game:home")


# =========================
# シッターからお迎え
# =========================

@login_required
@require_POST
@transaction.atomic
def pickup_sitter(request):

    save_data = get_save_data(request)

    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    # 既存のシッター終了処理を利用
    save_data, success, message = end_sitter(
        save_data,
        now=timezone.now()
    )

    if success:

        messages.success(
            request,
            "キャラクターが帰ってきました！"
        )

    else:

        messages.error(
            request,
            message
        )

    return redirect("real_time_game:home")

# =========================
# 家具・壁紙の操作
# =========================

@login_required
@require_POST
@transaction.atomic
def manage_item(request):

    save_data = get_save_data(request)

    # 同時操作によるデータの不整合を防止
    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    now = timezone.now()

    # 現在までの時間経過を反映
    save_data = apply_elapsed_time(
        save_data,
        now=now
    )

    items_url = (
        reverse("real_time_game:home")
        + "?menu=items"
    )

    # 育成開始前は操作できない
    if not save_data.has_started_game:

        messages.error(
            request,
            "育成を開始してから利用してください"
        )

        return redirect("real_time_game:home")

    # イントロ・チュートリアル中は家具を操作できない
    if (
            save_data.status == "playing"
            and save_data.tutorial_step != 4
    ):

        messages.error(
            request,
            "チュートリアル終了後に家具を利用できます"
        )

        return redirect("real_time_game:home")

    operation = request.POST.get("operation", "")
    item = request.POST.get("item", "")


    # =========================
    # NEWマークを消す
    # =========================

    if operation == "mark_seen":

        save_data.new_items = []

        save_data.save(
            update_fields=["new_items"]
        )

        return redirect(items_url)


    # =========================
    # 家具・壁紙の確認
    # =========================

    if item != "room-default":

        if (
            item not in ALL_ITEMS
            or item not in save_data.items
        ):

            messages.error(
                request,
                "所持していないアイテムです"
            )

            return redirect(items_url)

    item_name = ITEM_NAMES.get(
        item,
        "初期の壁紙"
    )

    update_fields = []
    log_action = ""
    result_message = ""


    # =========================
    # 家具を配置する
    # =========================

    if operation == "place":

        category = ITEM_CATEGORIES.get(item)

        if category is None:

            messages.error(
                request,
                "配置できないアイテムです"
            )

            return redirect(items_url)

        # 同じ種類の家具を取り除く
        placed_items = [

            placed_item

            for placed_item in save_data.placed_items

            if ITEM_CATEGORIES.get(placed_item)
            != category

        ]

        placed_items.append(item)

        # すでに配置されている場合
        if placed_items == save_data.placed_items:
            return redirect(items_url)

        save_data.placed_items = placed_items

        update_fields.append("placed_items")

        log_action = "家具配置"

        result_message = (
            f"{item_name}を配置しました"
        )


    # =========================
    # 家具をしまう
    # =========================

    elif operation == "remove":

        if (
            item not in ITEM_CATEGORIES
            or item not in save_data.placed_items
        ):
            return redirect(items_url)

        save_data.placed_items = [

            placed_item

            for placed_item in save_data.placed_items

            if placed_item != item

        ]

        update_fields.append("placed_items")

        log_action = "家具撤去"

        result_message = (
            f"{item_name}をしまいました"
        )


    # =========================
    # 壁紙を変更する
    # =========================

    elif operation == "wallpaper":

        if item not in (
            "room-default",
            "room-kawaii",
            "room-star",
            "room-sky",
        ):

            messages.error(
                request,
                "変更できない壁紙です"
            )

            return redirect(items_url)

        if save_data.room_wallpaper == item:
            return redirect(items_url)

        save_data.room_wallpaper = item

        update_fields.append("room_wallpaper")

        log_action = "壁紙変更"

        result_message = (
            f"{item_name}に変更しました"
        )


    # =========================
    # 不正な操作
    # =========================

    else:

        messages.error(
            request,
            "無効な操作です"
        )

        return redirect(items_url)


    # 操作したアイテムのNEWマークを消す
    if item in save_data.new_items:

        save_data.new_items = [

            new_item

            for new_item in save_data.new_items

            if new_item != item

        ]

        update_fields.append("new_items")


    # =========================
    # データの保存
    # =========================

    save_data.save(
        update_fields=update_fields
    )


    # =========================
    # 研究用ログの記録
    # =========================

    RealTimeActionLog.objects.create(

        user=request.user,

        game_round=save_data.game_round,

        action=log_action,

        timestamp=now,

        satisfaction=save_data.satisfaction,

        energy=save_data.energy,

        fullness=save_data.fullness,

        growth=save_data.growth,

        result=result_message,

        growth_delta=0,

        natural_growth_delta=0,

        elapsed_seconds=0,

    )

    messages.success(
        request,
        result_message
    )

    return redirect(items_url)


# ==========================================
# プレイ時間の定期記録
# ==========================================

@login_required
@require_POST
def play_heartbeat(request):

    page_view = request.POST.get("page_view") == "1"

    # 画面側の育成回数を取得
    try:
        expected_round = int(
            request.POST.get("game_round", "")
        )

    except (TypeError, ValueError):
        return JsonResponse(
            {"ok": False},
            status=400
        )

    play_session = touch_play_session(
        user=request.user,
        save_model=RealTimeSaveData,
        session_model=RealTimePlaySession,
        page_view=page_view,
        expected_round=expected_round,
    )

    # 前回の育成画面からの通信は拒否
    if play_session is None:
        return JsonResponse(
            {"ok": False},
            status=409
        )

    return JsonResponse({
        "ok": True,
        "session_id": play_session.pk
    })


# ==========================================
# プレイ終了の記録
# ==========================================

@login_required
@require_POST
def end_play_session(request):

    try:
        session_id = int(
            request.POST.get("session_id", "")
        )
    except (ValueError, TypeError):
        return JsonResponse(
            {"ok": False},
            status=400,
        )

    close_play_session(
        user=request.user,
        save_model=RealTimeSaveData,
        session_model=RealTimePlaySession,
        session_id=session_id,
    )

    return JsonResponse({
        "ok": True,
    })