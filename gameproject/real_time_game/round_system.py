from datetime import timedelta, time
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from play_session_system import close_play_session

from .models import (
    RealTimeSaveData,
    RealTimeActionLog,
    RealTimeMinigameSession,
    RealTimePlaySession,
)

from .time_system import (
    apply_elapsed_time,
    finish_sitter,
    sitter_end_time,
)


# =========================
# 新しい育成を開始する
# =========================

@transaction.atomic
def start_new_round(
        save_data,
        expected_round,
        now=None,
        *,
        reset=False
):

    # 同時操作を防止
    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    if now is None:
        now = timezone.now()

    # 時間経過を反映
    save_data = apply_elapsed_time(
        save_data,
        now=now
    )

    # 二重操作を防止
    if save_data.game_round != expected_round:

        return save_data, False, (
            "すでに新しい育成が開始されています"
        )

    # リセットの場合
    if reset:

        if save_data.status not in (
                "playing",
                "cleared",
                "game_over"
        ):
            return save_data, False, (
                "まだ育成が開始されていません"
            )

    # 通常の新しい育成の場合
    elif save_data.status not in (
            "cleared",
            "game_over"
    ):

        return save_data, False, (
            "現在の育成はまだ終了していません"
        )

    # =========================
    # 前回の育成終了時刻
    # =========================

    ended_at = (
        save_data.cleared_at
        or save_data.game_over_at
        or save_data.last_updated_at
    )

    # =========================
    # 終了していないミニゲーム
    # =========================

    sessions = (
        RealTimeMinigameSession.objects
        .select_for_update()
        .filter(
            user=save_data.user,
            status="playing"
        )
    )

    for session in sessions:

        session.status = "abandoned"

        session.ended_at = max(
            session.started_at,
            min(
                ended_at,
                session.started_at
                + timedelta(minutes=15)
            )
        )

        session.result = "育成終了"

        session.save(
            update_fields=[
                "status",
                "ended_at",
                "result"
            ]
        )

    # =========================
    # シッター利用の終了
    # =========================

    if save_data.sitter_started_at is not None:

        scheduled_end = sitter_end_time(
            save_data
        )

        sitter_finish_at = max(
            save_data.sitter_started_at,
            min(ended_at, scheduled_end)
        )

        finish_sitter(
            save_data,
            sitter_finish_at,
            auto=sitter_finish_at == scheduled_end
        )

    # =========================
    # 前回のプレイセッションを終了
    # =========================

    close_play_session(
        user=save_data.user,
        save_model=RealTimeSaveData,
        session_model=RealTimePlaySession,
        now=now,
    )

    # 60秒以上通信が途切れていたセッションなど、
    # 終了時刻が未確定の記録も終了させる
    sessions = RealTimePlaySession.objects.filter(
        user=save_data.user,
        game_round=save_data.game_round,
        logged_out_at__isnull=True
    )

    for session in sessions:
        session.logged_out_at = session.last_seen_at

        session.save(
            update_fields=["logged_out_at"]
        )

    # =========================
    # 前回の育成終了記録
    # =========================

    RealTimeActionLog.objects.create(
        user=save_data.user,
        game_round=save_data.game_round,
        action="reset" if reset else "round_end",
        timestamp=ended_at,
        satisfaction=save_data.satisfaction,
        energy=save_data.energy,
        fullness=save_data.fullness,
        growth=save_data.growth,
        result=(
            f"リセット（{save_data.status}）"
            if reset
            else save_data.status
        )
    )

    # =========================
    # 育成回数を増やす
    # =========================

    save_data.game_round += 1

    save_data.status = "playing"
    save_data.has_started_game = True

    # =========================
    # 基本パラメータの初期化
    # =========================

    save_data.satisfaction = Decimal("50")
    save_data.energy = Decimal("50")
    save_data.fullness = Decimal("50")
    save_data.growth = Decimal("0")

    # =========================
    # 時刻の初期化
    # =========================

    save_data.play_started_at = now
    save_data.last_updated_at = now

    save_data.cleared_at = None
    save_data.game_over_at = None
    save_data.last_good_bonus_at = None

    # =========================
    # ストックの初期化
    # =========================

    save_data.stock_ball = 2
    save_data.stock_food = 2
    save_data.stock_dodge = 2
    save_data.stock_dance = 2
    save_data.stock_timing = 2
    save_data.stock_count = 2
    save_data.stock_rest = 2

    save_data.stock_recovery_at = {}

    # =========================
    # 性格判定用データ
    # =========================

    save_data.play_count = 0
    save_data.healthy_food_count = 0
    save_data.snack_count = 0

    save_data.character_state = "normal"

    # =========================
    # 今回の育成に関する記録
    # =========================

    save_data.round_play_seconds = 0
    save_data.clear_time_seconds = 0

    save_data.natural_growth_total = Decimal("0")
    save_data.active_growth_total = Decimal("0")

    save_data.sitter_started_at = None
    save_data.sitter_total_seconds = 0

    # =========================
    # チュートリアル・成長通知
    # =========================

    # 新しい育成もイントロから開始する
    save_data.tutorial_step = 0
    save_data.notified_stage = 0

    # =========================
    # リセット時のみ初期化するデータ
    # =========================

    if reset:

        # 獲得した家具・壁紙
        save_data.items = []
        save_data.placed_items = []
        save_data.new_items = []

        # 部屋の壁紙
        save_data.room_wallpaper = "room-default"

        # 就寝時刻を23時に戻す
        save_data.bedtime = time(23, 0)

    # =========================
    # 保存
    # =========================

    # 家具・壁紙・累計行動回数などは
    # 変更しないことで引き継ぐ

    save_data.save()

    # =========================
    # 新しい育成の開始ログ
    # =========================

    RealTimeActionLog.objects.create(
        user=save_data.user,
        game_round=save_data.game_round,
        action="round_start",
        timestamp=now,
        satisfaction=save_data.satisfaction,
        energy=save_data.energy,
        fullness=save_data.fullness,
        growth=save_data.growth,
        result=(
            "リセット後の育成を開始"
            if reset
            else "新しい育成を開始"
        )
    )

    return save_data, True, (
        "ゲームをリセットしました！"
        if reset
        else "新しい育成を始めました！"
    )