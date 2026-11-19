
# リアルタイム型育成ゲームの基本報酬・家具抽選

from decimal import Decimal
import random
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from play_session_system import calculate_play_seconds_until

from .models import (
    RealTimeSaveData,
    RealTimeActionLog,
    RealTimeClearLog,
    RealTimePlaySession,
)

from .time_system import (
    apply_elapsed_time,
    is_sleep_time,
    is_sitter_time,
    clamp,
    PRECISION,
)

from .stock_system import consume_stock


# =========================
# 成長倍率
# =========================

GROWTH_MULTIPLIER = Decimal("1.2")


# =========================
# アイテムの表示名
# =========================

ITEM_NAMES = {
    'plant': '観葉植物',
    'sofa': 'ソファ',
    'rug': 'ラグ',
    'clock': '時計',

    'room-kawaii': 'かわいい壁紙',
    'room-star': '星空の壁紙',
    'room-sky': '空の壁紙',

    'sofa-star': '星のソファ',
    'plant-star': '星の観葉植物',
    'rug-star': '星のラグ',
    'clock-star': '星の時計',

    'sofa-kawaii': 'かわいいソファ',
    'plant-kawaii': 'かわいい観葉植物',
    'rug-kawaii': 'かわいいラグ',
    'clock-kawaii': 'かわいい時計',
}


# =========================
# アイテムのシリーズ分類
# =========================

ITEM_TYPES = {
    # skyシリーズ（通常家具）
    'plant': 'sky',
    'sofa': 'sky',
    'rug': 'sky',
    'clock': 'sky',

    # 星シリーズ
    'sofa-star': 'star',
    'plant-star': 'star',
    'rug-star': 'star',
    'clock-star': 'star',

    # かわいいシリーズ
    'sofa-kawaii': 'kawaii',
    'plant-kawaii': 'kawaii',
    'rug-kawaii': 'kawaii',
    'clock-kawaii': 'kawaii',

    # 壁紙
    'room-kawaii': 'wallpaper',
    'room-star': 'wallpaper',
    'room-sky': 'wallpaper',
}


# =========================
# シリーズ別の抽選確率
# =========================

ITEM_TYPE_WEIGHTS = {
    'kawaii': 40,
    'sky': 30,
    'star': 20,
    'wallpaper': 10,
}


# =========================
# ミニゲームの基本報酬
# =========================
# 満足度・体力・満腹度・成長度・メッセージ
# 残りライフ0〜3の順番
# 成長倍率は報酬計算時に適用する

RESULT_TABLES = {

    # 好きなごはん選び
    'food': [
        (5, 2, 12, 0, "あまり選べなかった…"),
        (8, 3, 18, 0, "なんとか食べられた"),
        (12, 4, 24, 1, "好物をしっかり選べた！"),
        (20, 5, 30, 2, "完璧に好物だけ選べた！大満足！"),
    ],

    # 火加減チャレンジ
    'timing': [
        (2, 3, 15, 0, "料理があまりうまくいかなかった…"),
        (4, 6, 25, 1, "なんとか料理できた！"),
        (6, 9, 35, 2, "上手に料理できた！"),
        (10, 12, 45, 3, "完璧な料理ができた！大満足！"),
    ],

    # 食材かぞえ
    'count': [
        (8, -2, 5, 0, "食材をうまく数えられなかった…"),
        (14, -2, 8, 1, "なんとか数えられた！"),
        (20, -2, 10, 1, "上手に食材を数えられた！"),
        (28, -2, 14, 2, "全問正解！食材を完璧に数えられた！"),
    ],

    # 障害物よけ
    'dodge': [
        (3, -15, -10, 0, "うまく避けられなかった…"),
        (6, -12, -10, 1, "なんとか避けられた！"),
        (10, -10, -10, 2, "上手に避けられた！"),
        (14, -8, -10, 3, "完璧！一度も当たらなかった！"),
    ],
}


# =========================
# ダンスまねのクリア報酬
# =========================
# 満足度・成長度

DANCE_CLEAR_TABLE = {
    'easy': (8, 1),
    'normal': (12, 2),
    'hard': (16, 3),
    'oni': (20, 4),
}


# =========================
# 全アイテム
# =========================

ALL_ITEMS = [
    'plant', 'sofa', 'rug', 'clock',

    'room-kawaii', 'room-star', 'room-sky',

    'sofa-star', 'plant-star',
    'rug-star', 'clock-star',

    'sofa-kawaii', 'plant-kawaii',
    'rug-kawaii', 'clock-kawaii',
]


# =========================
# 行動報酬のデータ形式
# =========================

@dataclass(frozen=True)
class ActionReward:

    satisfaction: int
    energy: int
    fullness: int
    growth: Decimal
    message: str
    success: bool


# =========================
# 基本報酬の計算
# =========================

def get_basic_reward(
        action,
        *,
        energy=50,
        score=0,
        lives=0,
        result="fail",
        difficulty="easy",
        in_tutorial=False
):

    """
    行動・ミニゲームの基本報酬を返す。

    ストック消費、追加イベント、
    データベースへの保存は別の処理で行う。
    """

    # -------------------------
    # 休む
    # -------------------------

    if action == "rest":

        if energy <= 40:
            sat = 8
            eng = 35
        else:
            sat = 0
            eng = 25

        return ActionReward(
            sat,
            eng,
            0 if in_tutorial else -3,
            Decimal("0"),
            "ゆっくり休んだ！",
            True
        )

    # -------------------------
    # 入力値の確認
    # -------------------------

    if type(score) is not int or score < 0:
        raise ValueError(
            "score must be a nonnegative integer"
        )

    if type(lives) is not int or not 0 <= lives <= 3:
        raise ValueError(
            "lives must be between 0 and 3"
        )

    if difficulty not in DANCE_CLEAR_TABLE:
        raise ValueError("invalid difficulty")

    # -------------------------
    # ライフ制ミニゲーム
    # -------------------------

    if action in RESULT_TABLES:

        sat, eng, full, growth, message = (
            RESULT_TABLES[action][lives]
        )

        success = lives >= 1

        # 障害物よけの追加ボーナス
        if action == "dodge" and score >= 5:

            sat += 3
            growth += 1

            message += " アイテムもたくさん取れた！"

    # -------------------------
    # ボールキャッチ
    # -------------------------

    elif action == "ball":

        if score < 10:

            sat = 10
            growth = 1
            message = "少し遊べた！"

        elif score < 15:

            sat = 20
            growth = 2
            message = "たくさん遊べて楽しそう！"

        else:

            sat = 30
            growth = 3
            message = "大満足だったみたい！"

        eng = 0 if in_tutorial else -10
        full = 0 if in_tutorial else -10

        success = score >= 10

    # -------------------------
    # ダンスまね
    # -------------------------

    elif action == "dance":

        if result not in ("clear", "fail"):
            raise ValueError("invalid dance result")

        success = result == "clear"

        eng = -8
        full = -8

        if success:

            sat, growth = DANCE_CLEAR_TABLE[difficulty]

            message = "完璧なダンス！"

        else:

            sat = 4
            growth = 0

            message = "惜しかった！また挑戦しよう！"

    else:

        raise ValueError("unknown action")

    # -------------------------
    # 成長倍率を適用して返す
    # -------------------------

    return ActionReward(
        sat,
        eng,
        full,
        Decimal(growth) * GROWTH_MULTIPLIER,
        message,
        success
    )


# =========================
# 家具・壁紙の抽選
# =========================

def draw_item(items, character_state):

    """
    未獲得アイテムを1個抽選する。
    獲得しなかった場合はNoneを返す。
    所持アイテム自体は変更しない。
    """

    # Happy状態のときだけ抽選する
    if character_state != "happy":
        return None

    # 未獲得のアイテム
    not_owned = [
        item
        for item in ALL_ITEMS
        if item not in items
    ]

    # 獲得確率は30%
    if not not_owned or random.randint(1, 100) > 30:
        return None

    # 未獲得アイテムが存在するシリーズ
    available = [
        kind
        for kind in ITEM_TYPE_WEIGHTS
        if any(
            ITEM_TYPES[item] == kind
            for item in not_owned
        )
    ]

    # シリーズを抽選する
    kind = random.choices(
        available,
        weights=[
            ITEM_TYPE_WEIGHTS[k]
            for k in available
        ],
        k=1
    )[0]

    # 選ばれたシリーズからアイテムを1つ抽選
    return random.choice([
        item
        for item in not_owned
        if ITEM_TYPES[item] == kind
    ])


# =========================
# 行動の種類
# =========================

FOOD_ACTIONS = (
    "food", "timing", "count"
)

PLAY_ACTIONS = (
    "ball", "dodge", "dance"
)

ACTION_NAMES = {
    "rest": "休む",
    "ball": "ボールキャッチ",
    "food": "好きなごはん選び",
    "timing": "火加減チャレンジ",
    "count": "食材かぞえ",
    "dodge": "障害物よけ",
    "dance": "ダンスまね",
}

GOOD_BONUS_INTERVAL = timedelta(hours=3)


# =========================
# 成長ボーナス
# =========================

def get_good_growth_bonus(save_data, now):

    """
    良好な状態による成長ボーナスを計算する。
    3時間に1回まで獲得できる。
    """

    if save_data.satisfaction < 80:
        return Decimal("0")

    last = save_data.last_good_bonus_at

    if last is not None:

        if now - last < GOOD_BONUS_INTERVAL:
            return Decimal("0")

    if save_data.energy >= 80:
        bonus = Decimal("2")
    else:
        bonus = Decimal("1")

    save_data.last_good_bonus_at = now

    return bonus


# =========================
# パラメータ依存イベント
# =========================

def apply_parameter_events(
        save_data,
        action,
        now,
        in_tutorial=False
):

    """
    基本報酬反映後のパラメータに応じて
    追加イベントを発生させる。
    """

    messages = []

    tutorial_bonus = Decimal("0")

    save_data.character_state = "normal"

    # -------------------------
    # 体力が低い
    # -------------------------

    if save_data.energy <= 30:

        save_data.growth -= 2
        save_data.character_state = "tired"



    # -------------------------
    # 満足度が高い
    # -------------------------

    if save_data.satisfaction >= 80:

        save_data.character_state = "happy"

        if in_tutorial:
            tutorial_bonus += Decimal("1")

    # -------------------------
    # 満腹すぎる
    # -------------------------

    if save_data.fullness >= 90:

        save_data.satisfaction -= 5
        save_data.growth -= 2
        save_data.character_state = "tired"



    # -------------------------
    # 満腹なのに食事をした
    # -------------------------

    if (
        save_data.fullness >= 90
        and action in FOOD_ACTIONS
    ):

        save_data.satisfaction -= 10
        save_data.energy -= 5
        save_data.character_state = "tired"

    # -------------------------
    # 元気なのに休む
    # -------------------------

    if (
        save_data.energy >= 90
        and action == "rest"
    ):

        save_data.satisfaction -= 15
        save_data.growth -= 2
        save_data.character_state = "tired"



    # -------------------------
    # 疲れているのに遊ぶ
    # -------------------------

    if (
        save_data.energy <= 30
        and action in PLAY_ACTIONS
    ):

        save_data.energy -= 10
        save_data.satisfaction -= 5
        save_data.character_state = "tired"

    # -------------------------
    # 空腹なのに遊ぶ
    # -------------------------

    if (
        save_data.fullness <= 30
        and action in PLAY_ACTIONS
    ):

        save_data.satisfaction -= 10
        save_data.character_state = "tired"



    # -------------------------
    # 絶好調
    # -------------------------

    if (
            save_data.satisfaction >= 80
            and save_data.energy >= 80
    ):

        save_data.character_state = "happy"

        if in_tutorial:
            tutorial_bonus += Decimal("2")

    # -------------------------
    # 弱っている状態
    # -------------------------

    if (
        save_data.energy <= 20
        and save_data.fullness <= 20
    ):

        save_data.growth -= 2
        save_data.character_state = "tired"

    # -------------------------
    # 良い状態による成長ボーナス
    # -------------------------

    if in_tutorial:

        # 練習中はターン制と同じ成長ボーナス
        bonus = tutorial_bonus

    else:

        # 通常育成中は3時間に1回まで
        bonus = get_good_growth_bonus(
            save_data, now
        )

    save_data.growth += bonus

    if bonus > 0:
        messages.append(
            "元気に成長した！"
        )

    return messages, bonus


# =========================
# 行動による累計回数の更新
# =========================

def record_action_count(save_data, action, success):

    action_field = f"action_{action}_count"

    setattr(
        save_data,
        action_field,
        getattr(save_data, action_field) + 1
    )

    if action == "rest":
        return

    # ミニゲームのプレイ回数
    play_field = f"minigame_{action}_play"

    setattr(
        save_data,
        play_field,
        getattr(save_data, play_field) + 1
    )

    # ミニゲームの成功回数
    if success:

        success_field = (
            f"minigame_{action}_success"
        )

        setattr(
            save_data,
            success_field,
            getattr(save_data, success_field) + 1
        )

    # キャラクターの性格判定用
    if action in ("food", "timing"):

        save_data.healthy_food_count += 1

    elif action == "count":

        save_data.snack_count += 1

    elif action in PLAY_ACTIONS:

        save_data.play_count += 1


# =========================
# 育成終了の判定
# =========================

def check_action_game_end(save_data, now):

    if save_data.status != "playing":
        return

    # ゲームオーバーを優先
    if save_data.energy <= 0:

        save_data.status = "game_over"
        save_data.game_over_at = now
        save_data.game_over_count += 1

    elif save_data.growth >= 100:

        save_data.status = "cleared"
        save_data.cleared_at = now
        save_data.clear_count += 1

        if save_data.play_started_at:

            save_data.clear_time_seconds = max(
                0,
                int(
                    (
                        now - save_data.play_started_at
                    ).total_seconds()
                )
            )


# =========================
# 行動によるクリア記録
# =========================
def save_action_clear_log(save_data):

    if save_data.status != "cleared":
        return

    RealTimeClearLog.objects.get_or_create(
        user=save_data.user,
        game_round=save_data.game_round,
        defaults={
            "clear_number": save_data.clear_count,
            "cleared_at": save_data.cleared_at,

            "play_seconds": calculate_play_seconds_until(
                user=save_data.user,
                session_model=RealTimePlaySession,
                game_round=save_data.game_round,
                ended_at=save_data.cleared_at,
            ),

            "elapsed_seconds": save_data.clear_time_seconds,
            "natural_growth_total": save_data.natural_growth_total,
            "active_growth_total": save_data.active_growth_total,
            "sitter_seconds": save_data.sitter_total_seconds,
        }
    )

# =========================
# 成長段階
# =========================

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


# =========================
# 行動結果の反映
# =========================

@transaction.atomic
def apply_action(
        save_data,
        action,
        *,
        score=0,
        lives=0,
        result="fail",
        difficulty="easy",
        now=None,
        minigame_session=None
):

    """
    行動結果を育成データへ反映する内部処理。

    戻り値：
    最新の育成データ、実行可否、結果情報

    現段階ではミニゲームの開始・終了を
    分離せず、一度に結果を反映する。
    """

    if now is None:
        now = timezone.now()

    if action not in ACTION_NAMES:
        raise ValueError("unknown action")

    # 同時更新を防止する
    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    # -------------------------
    # 時間経過を反映
    # -------------------------

    save_data = apply_elapsed_time(
        save_data,
        now=now
    )

    # -------------------------
    # 行動可能か確認
    # -------------------------

    if save_data.status != "playing":

        return save_data, False, {
            "message": "育成が終了しています"
        }

    if now < save_data.last_updated_at:

        return save_data, False, {
            "message": "無効な行動時刻です"
        }

    # 現在のチュートリアル段階
    tutorial_step = save_data.tutorial_step

    tutorial_active = (
            tutorial_step in (1, 2, 3)
    )

    # イントロ中は行動できない
    if tutorial_step == 0:
        return save_data, False, {
            "message": "先にイントロを確認してください"
        }

    # 追加説明中は行動できない
    if tutorial_step == 5:
        return save_data, False, {
            "message": "先に追加説明を確認してください"
        }

    # チュートリアル中は指定された行動のみ許可
    if tutorial_active:

        required_action = {
            1: "food",
            2: "dance",
            3: "rest",
        }.get(tutorial_step)

        if action != required_action:
            return save_data, False, {
                "message": "チュートリアルに沿って行動してください"
            }

    # 通常育成中の睡眠判定
    if not tutorial_active and is_sleep_time(
            now, save_data.bedtime
    ):
        return save_data, False, {
            "message": "キャラクターは睡眠中です"
        }

    # 通常育成中のシッター判定
    if not tutorial_active and is_sitter_time(
            save_data, now
    ):
        return save_data, False, {
            "message": "シッターを利用中です"
        }


    # -------------------------
    # チュートリアル判定
    # -------------------------

    if minigame_session is not None:

        from .models import RealTimeMinigameSession

        minigame_session = (
            RealTimeMinigameSession.objects
            .select_for_update()
            .get(pk=minigame_session.pk)
        )

        if (
            minigame_session.user_id != save_data.user_id
            or minigame_session.game_round != save_data.game_round
            or minigame_session.action != action
            or minigame_session.status != "playing"
            or now < minigame_session.started_at
            or (
                not minigame_session.is_tutorial
                and not minigame_session.stock_consumed
            )
        ):

            return save_data, False, {
                "message": "無効なミニゲームです"
            }

        # 開始時と終了時のチュートリアル状態を確認
        if minigame_session.is_tutorial != tutorial_active:
            return save_data, False, {
                "message": "現在の育成状態と一致しません"
            }

        in_tutorial = minigame_session.is_tutorial
        difficulty = minigame_session.difficulty

    else:

        in_tutorial = (
            save_data.tutorial_step in (1, 2, 3)
        )

        # -------------------------
        # 難易度の確認
        # -------------------------

        stage = get_growth_stage(
            save_data.growth
        )

        difficulty_levels = (
            "easy", "normal", "hard", "oni"
        )

        unlocked = difficulty_levels[
            :min(stage + 1, 4)
        ]

        if in_tutorial:

            difficulty = "easy"

        elif difficulty not in unlocked:

            return save_data, False, {
                "message": "選択できない難易度です"
            }


    # -------------------------
    # 基本報酬の計算
    # -------------------------

    reward = get_basic_reward(
        action,
        energy=save_data.energy,
        score=score,
        lives=lives,
        result=result,
        difficulty=difficulty,
        in_tutorial=in_tutorial
    )

    # -------------------------
    # ストック消費
    # -------------------------

    if not in_tutorial and minigame_session is None:

        if not consume_stock(
            save_data, action, now=now
        ):

            return save_data, False, {
                "message": "ストックがありません"
            }

    # -------------------------
    # 行動前の成長度
    # -------------------------

    before_growth = Decimal(
        save_data.growth
    )

    # -------------------------
    # 基本報酬の反映
    # -------------------------

    save_data.satisfaction += reward.satisfaction
    save_data.energy += reward.energy
    save_data.fullness += reward.fullness
    save_data.growth += reward.growth

    # -------------------------
    # 追加イベント
    # -------------------------

    messages, bonus = apply_parameter_events(
        save_data,
        action,
        now,
        in_tutorial=in_tutorial
    )

    # -------------------------
    # 家具・壁紙の抽選
    # -------------------------

    new_item = draw_item(
        save_data.items,
        save_data.character_state
    )

    if new_item is not None:

        save_data.items = (
            list(save_data.items) + [new_item]
        )

        save_data.new_items = (
            list(save_data.new_items) + [new_item]
        )

    # -------------------------
    # 上限・下限の調整
    # -------------------------

    for field in (
        "satisfaction",
        "energy",
        "fullness",
        "growth",
    ):

        value = Decimal(
            getattr(save_data, field)
        )

        setattr(
            save_data,
            field,
            clamp(value).quantize(PRECISION)
        )

    # -------------------------
    # 能動的成長量の記録
    # -------------------------

    growth_delta = (
        save_data.growth - before_growth
    ).quantize(PRECISION)

    save_data.active_growth_total = (
        Decimal(save_data.active_growth_total)
        + growth_delta
    ).quantize(PRECISION)

    # -------------------------
    # 行動回数の記録
    # -------------------------

    # チュートリアル中も行動回数を集計
    record_action_count(
        save_data,
        action,
        reward.success
    )

    if in_tutorial:

        # -------------------------
        # チュートリアルの進行
        # -------------------------

        if tutorial_step == 1 and action == "food":

            save_data.tutorial_step = 2

        elif tutorial_step == 2 and action == "dance":

            save_data.tutorial_step = 3


        elif tutorial_step == 3 and action == "rest":

            # リアルタイム型の追加説明へ移行

            save_data.tutorial_step = 5

            # 追加説明中も時間経過を停止する

            save_data.last_updated_at = now

    # -------------------------
    # 育成終了の判定
    # -------------------------

    check_action_game_end(
        save_data, now
    )

    # -------------------------
    # 育成データの保存
    # -------------------------

    save_data.save()

    save_action_clear_log(save_data)

    # -------------------------
    # 行動ログの結果文字列
    # -------------------------

    if action == "ball":

        result_text = f"スコア:{score}"

    elif action == "dodge":

        result_text = (
            f"ライフ:{lives} スコア:{score}"
        )

    elif action in FOOD_ACTIONS:

        result_text = f"ライフ:{lives}"

    elif action == "dance":

        result_text = result

    else:

        result_text = ""

    if action != "rest":

        result_text += f" 難易度:{difficulty}"

    if in_tutorial:

        result_text += " [練習]"

    # -------------------------
    # 研究用行動ログの保存
    # -------------------------

    RealTimeActionLog.objects.create(
        user=save_data.user,
        game_round=save_data.game_round,
        action=ACTION_NAMES[action],
        timestamp=now,
        satisfaction=save_data.satisfaction,
        energy=save_data.energy,
        fullness=save_data.fullness,
        growth=save_data.growth,
        result=result_text.strip(),
        growth_delta=growth_delta,
        natural_growth_delta=Decimal("0"),
        elapsed_seconds=0,
    )

    # -------------------------
    # 画面表示用の結果
    # -------------------------

    return save_data, True, {
        "message": reward.message,
        "event_messages": messages,
        "growth_delta": growth_delta,
        "good_bonus": bonus,
        "new_item": new_item,
        "success": reward.success,
    }
