
from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from .models import (
    RealTimeSaveData,
    RealTimeMinigameSession,
)

from .time_system import (
    apply_elapsed_time,
    is_sleep_time,
    is_sitter_time,
)

from .stock_system import consume_stock

from .action_system import (
    apply_action,
    get_growth_stage,
    get_basic_reward,
)


# =========================
# ミニゲームの設定
# =========================

MINIGAME_ACTIONS = (
    "ball",
    "food",
    "timing",
    "count",
    "dodge",
    "dance",
)

DIFFICULTY_LEVELS = (
    "easy",
    "normal",
    "hard",
    "oni",
)

# 結果を受け付ける最大時間
SESSION_TIMEOUT = timedelta(minutes=15)


# =========================
# 途中離脱の記録
# =========================

def mark_abandoned(session, now, reason):

    session.status = "abandoned"
    session.ended_at = now
    session.result = reason

    session.save(
        update_fields=[
            "status",
            "ended_at",
            "result",
        ]
    )


# =========================
# 識別IDから記録を取得
# =========================

def get_session(save_data, token):

    try:

        token = UUID(str(token))

    except (ValueError, TypeError):

        return None

    return (
        RealTimeMinigameSession.objects
        .select_for_update()
        .filter(
            user_id=save_data.user_id,
            token=token,
        )
        .first()
    )


# =========================
# ミニゲーム開始
# =========================

@transaction.atomic
def start_minigame(
        save_data,
        action,
        difficulty="easy",
        now=None
):

    """
    戻り値：
    育成データ、成功 여부、結果情報
    """

    now = now or timezone.now()

    save_data = apply_elapsed_time(
        save_data,
        now=now
    )

    # -------------------------
    # 行動可能か確認
    # -------------------------

    if action not in MINIGAME_ACTIONS:

        return save_data, False, {
            "message": "無効なミニゲームです"
        }

    if (
        save_data.status != "playing"
        or now < save_data.last_updated_at
    ):

        return save_data, False, {
            "message": "現在は育成できません"
        }

    # -------------------------
    # チュートリアル判定
    # -------------------------

    in_tutorial = (
            save_data.tutorial_step in (1, 2, 3)
    )

    # イントロ中はミニゲームを開始できない
    if save_data.tutorial_step == 0:
        return save_data, False, {
            "message": "先にイントロを確認してください"
        }

    # 追加説明中はミニゲームを開始できない
    if save_data.tutorial_step == 5:
        return save_data, False, {
            "message": "先に追加説明を確認してください"
        }

    # チュートリアル中の行動制限
    if in_tutorial:

        required_action = {
            1: "food",
            2: "dance",
            3: "rest",
        }.get(save_data.tutorial_step)

        if action != required_action:
            return save_data, False, {
                "message": "チュートリアルに沿って行動してください"
            }

    # 通常育成中のみ睡眠を判定
    if not in_tutorial and is_sleep_time(
            now, save_data.bedtime
    ):
        return save_data, False, {
            "message": "キャラクターは睡眠中です"
        }

    # 通常育成中のみシッターを判定
    if not in_tutorial and is_sitter_time(
            save_data, now
    ):
        return save_data, False, {
            "message": "シッターを利用中です"
        }

    # -------------------------
    # チュートリアル・難易度
    # -------------------------

    if in_tutorial:

        difficulty = "easy"

    else:

        stage = get_growth_stage(
            save_data.growth
        )

        unlocked = DIFFICULTY_LEVELS[
            :min(stage + 1, 4)
        ]

        if difficulty not in unlocked:

            return save_data, False, {
                "message": "未解放の難易度です"
            }

    # -------------------------
    # プレイ中の記録を確認
    # -------------------------

    previous = (
        RealTimeMinigameSession.objects
        .select_for_update()
        .filter(
            user_id=save_data.user_id,
            status="playing"
        )
        .first()
    )

    if previous is not None:

        expires_at = (
            previous.started_at + SESSION_TIMEOUT
        )

        if previous.game_round != save_data.game_round:

            mark_abandoned(
                previous,
                min(now, expires_at),
                "育成回の変更"
            )

        elif now >= expires_at:

            mark_abandoned(
                previous,
                expires_at,
                "制限時間超過"
            )

        else:

            return save_data, False, {
                "message": "プレイ中のミニゲームがあります"
            }

    # -------------------------
    # ストック消費
    # -------------------------

    if not in_tutorial:

        if not consume_stock(
            save_data,
            action,
            now=now
        ):

            return save_data, False, {
                "message": "ストックがありません"
            }

    save_data.save()

    # -------------------------
    # 開始記録
    # -------------------------

    session = RealTimeMinigameSession.objects.create(
        user=save_data.user,
        game_round=save_data.game_round,
        action=action,
        difficulty=difficulty,
        started_at=now,
        is_tutorial=in_tutorial,
        stock_consumed=not in_tutorial,
    )

    return save_data, True, {
        "message": "ミニゲーム開始",
        "token": str(session.token),
        "difficulty": session.difficulty,
    }


# =========================
# ミニゲーム終了
# =========================

@transaction.atomic
def finish_minigame(
        save_data,
        token,
        *,
        score=0,
        lives=0,
        result="fail",
        now=None
):

    now = now or timezone.now()

    save_data = apply_elapsed_time(
        save_data,
        now=now
    )

    session = get_session(
        save_data, token
    )

    # -------------------------
    # 二重反映・不正操作防止
    # -------------------------

    if (
        session is None
        or session.status != "playing"
    ):

        return save_data, False, {
            "message": "無効または終了済みです"
        }

    if (
        now < session.started_at
        or now < save_data.last_updated_at
    ):

        return save_data, False, {
            "message": "無効な終了時刻です"
        }

    if session.game_round != save_data.game_round:

        mark_abandoned(
            session,
            min(
                now,
                session.started_at + SESSION_TIMEOUT
            ),
            "育成回の変更"
        )

        return save_data, False, {
            "message": "以前の育成の記録です"
        }

    # -------------------------
    # 制限時間
    # -------------------------

    expires_at = (
        session.started_at + SESSION_TIMEOUT
    )

    if now >= expires_at:

        mark_abandoned(
            session,
            expires_at,
            "制限時間超過"
        )

        return save_data, False, {
            "message": "結果受付時間を過ぎています"
        }

    # -------------------------
    # 結果の入力値確認
    # -------------------------

    try:

        get_basic_reward(
            session.action,
            energy=save_data.energy,
            score=score,
            lives=lives,
            result=result,
            difficulty=session.difficulty,
            in_tutorial=session.is_tutorial
        )

    except ValueError:

        return save_data, False, {
            "message": "無効なゲーム結果です"
        }

    # -------------------------
    # 報酬を反映する
    # -------------------------

    save_data, success, info = apply_action(
        save_data,
        session.action,
        score=score,
        lives=lives,
        result=result,
        difficulty=session.difficulty,
        now=now,
        minigame_session=session
    )

    if not success:

        mark_abandoned(
            session,
            now,
            info["message"]
        )

        return save_data, False, info

    # -------------------------
    # 終了記録
    # -------------------------

    session.status = "completed"
    session.ended_at = now
    session.score = score
    session.lives = lives
    session.success = info["success"]
    session.growth_delta = info["growth_delta"]

    session.result = (
        "成功" if info["success"] else "失敗"
    )

    session.save()

    return save_data, True, info


# =========================
# ミニゲーム中断
# =========================

@transaction.atomic
def abandon_minigame(
        save_data,
        token,
        now=None
):

    now = now or timezone.now()

    save_data = apply_elapsed_time(
        save_data,
        now=now
    )

    session = get_session(
        save_data, token
    )

    if (
        session is None
        or session.status != "playing"
        or now < session.started_at
        or now < save_data.last_updated_at
    ):

        return save_data, False, {
            "message": "中断できるゲームがありません"
        }

    expires_at = (
        session.started_at + SESSION_TIMEOUT
    )

    mark_abandoned(
        session,
        min(now, expires_at),
        "制限時間超過" if now >= expires_at
        else "途中離脱"
    )

    # 消費したストックは返却しない

    return save_data, True, {
        "message": "ミニゲームを中断しました"
    }
