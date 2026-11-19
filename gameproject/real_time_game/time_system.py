from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from play_session_system import calculate_play_seconds_until

from .stock_system import recover_stocks

from .models import (
    RealTimeSaveData,
    RealTimeActionLog,
    RealTimeClearLog,
    RealTimeSitterLog,
    RealTimePlaySession,
)

# =========================
# 1時間あたりの変化量
# =========================

NORMAL_SATISFACTION = Decimal("-4")
NORMAL_ENERGY = Decimal("-1.5")
NORMAL_FULLNESS = Decimal("-6")

SLEEP_ENERGY = Decimal("8")

NORMAL_GROWTH = Decimal("1.2")
LOW_GROWTH = Decimal("0.3")

ZERO = Decimal("0")
MAX_VALUE = Decimal("100")

# 保存時の小数点以下の桁数
PRECISION = Decimal("0.0001")


def clamp(value):
    """パラメータを0〜100の範囲に収める"""
    return max(ZERO, min(MAX_VALUE, value))


def sitter_end_time(save_data):
    if save_data.sitter_started_at is None:
        return None
    day = timezone.localtime(save_data.sitter_started_at).date()
    return timezone.make_aware(datetime.combine(day, time(19, 0)))


def is_sitter_time(save_data, dt):
    end = sitter_end_time(save_data)
    return end is not None and save_data.sitter_started_at <= dt < end


def record_sitter_action(save_data, action, now, result):
    RealTimeActionLog.objects.create(
        user=save_data.user, game_round=save_data.game_round,
        action=action, timestamp=now, result=result,
        satisfaction=save_data.satisfaction, energy=save_data.energy,
        fullness=save_data.fullness, growth=save_data.growth,
    )


def finish_sitter(save_data, end, auto=False):
    start = save_data.sitter_started_at
    if start is None:
        return
    log, _ = RealTimeSitterLog.objects.get_or_create(
        user=save_data.user, game_round=save_data.game_round,
        started_at=start,
    )
    log.ended_at = end
    log.auto_ended = auto
    log.save(update_fields=["ended_at", "auto_ended"])
    save_data.sitter_total_seconds += max(0, int((end-start).total_seconds()))
    save_data.sitter_started_at = None
    save_data.save(update_fields=["sitter_total_seconds", "sitter_started_at"])
    record_sitter_action(save_data, "sitter_auto_end" if auto else "sitter_end",
                         end, "自動お迎え" if auto else "お迎え")


def is_sleep_time(dt, bedtime=time(23, 0)):
    """
    プレイヤーが設定した入眠時刻から
    8時間以内であれば睡眠中と判定する。
    """

    local_dt = timezone.localtime(dt)

    # 現在時刻を秒数に変換
    current_seconds = (
        local_dt.hour * 3600
        + local_dt.minute * 60
        + local_dt.second
        + local_dt.microsecond / 1000000
    )

    # 入眠時刻を秒数に変換
    bedtime_seconds = (
        bedtime.hour * 3600
        + bedtime.minute * 60
        + bedtime.second
        + bedtime.microsecond / 1000000
    )

    # 入眠時刻からの経過時間
    elapsed_seconds = (
        current_seconds - bedtime_seconds
    ) % 86400

    # 入眠から8時間以内なら睡眠中
    return elapsed_seconds < 8 * 3600




def next_time_boundary(dt, bedtime=time(23, 0)):
    """
    現在時刻より後に訪れる
    入眠時刻または起床時刻を取得する。
    """

    local_dt = timezone.localtime(dt)
    today = local_dt.date()
    tz = timezone.get_current_timezone()

    boundaries = []

    # 前日・当日・翌日の睡眠時間を確認
    for offset in [-1, 0, 1]:

        target_date = today + timedelta(days=offset)

        sleep_start = timezone.make_aware(
            datetime.combine(target_date, bedtime),
            tz
        )

        # 入眠から8時間後に起床
        sleep_end = sleep_start + timedelta(hours=8)

        boundaries.append(sleep_start)
        boundaries.append(sleep_end)

    return min(
        boundary
        for boundary in boundaries
        if boundary > dt
    )



def decimal_seconds(start, end):
    """経過秒数をDecimalで取得"""
    delta = end - start
    return (
        Decimal(delta.days) * Decimal("86400")
        + Decimal(delta.seconds)
        + Decimal(delta.microseconds) / Decimal("1000000")
    )


def hours_between(start, end):
    return decimal_seconds(start, end) / Decimal("3600")


def seconds_to_timedelta(seconds):
    return timedelta(seconds=float(seconds))


def time_until_threshold(value, rate, threshold):
    """
    現在値から指定の境界値までに必要な秒数。
    rateは1時間あたりの変化量。
    """
    if rate == ZERO:
        return None

    hours = (threshold - value) / rate

    if hours <= ZERO:
        return None

    return hours * Decimal("3600")


@transaction.atomic
def apply_elapsed_time(save_data, now=None):
    """
    最終更新から現在までの時間経過を反映する。

    ・通常時の自然減少
    ・睡眠中の体力回復
    ・自然成長
    ・体力0によるゲームオーバー

    シッターの時間経過を反映。ストック回復は別途実装。
    """

    if now is None:
        now = timezone.now()

    RealTimeSaveData.objects.select_for_update().get(pk=save_data.pk)
    save_data.refresh_from_db()

    # 育成が始まっていなければ変化させない
    if save_data.status != "playing":
        return save_data

    start = save_data.last_updated_at

    # 過去の時刻では更新しない
    if start > now:
        return save_data

    # =========================
    # イントロ・チュートリアル中
    # =========================

    if save_data.tutorial_step in (0, 1, 2, 3, 5):
        # パラメータやストックは変化させず、
        # 最終更新時刻だけを現在時刻に更新する
        save_data.last_updated_at = now

        save_data.save(
            update_fields=["last_updated_at"]
        )

        return save_data

    # 経過時間がなくてもストックを確認する
    if start == now:
        recover_stocks(save_data, now=now)

        save_data.save(
            update_fields=[
                "stock_ball",
                "stock_food",
                "stock_dodge",
                "stock_dance",
                "stock_timing",
                "stock_count",
                "stock_rest",
                "stock_recovery_at",
            ]
        )

        return save_data

    satisfaction = Decimal(save_data.satisfaction)
    energy = Decimal(save_data.energy)
    fullness = Decimal(save_data.fullness)
    growth = Decimal(save_data.growth)

    natural_added = ZERO
    cursor = start

    # 状態が変化する境界ごとに計算する
    while cursor < now:

        boundary = min(
            next_time_boundary(cursor, save_data.bedtime),
            now
        )

        sitter_end = sitter_end_time(save_data)
        if sitter_end is not None and cursor < sitter_end:
            boundary = min(boundary, sitter_end)

        # -------------------------
        # 睡眠時間
        # -------------------------
        if is_sleep_time(cursor, save_data.bedtime):

            rate_energy = SLEEP_ENERGY

            hours = hours_between(cursor, boundary)

            energy = clamp(energy + rate_energy * hours)

        elif is_sitter_time(save_data, cursor):
            # 睡眠以外のシッター利用中は状態を維持
            pass

        # -------------------------
        # 通常時間
        # -------------------------
        else:

            rate_satisfaction = (
                NORMAL_SATISFACTION if satisfaction > ZERO else ZERO
            )

            rate_fullness = (
                NORMAL_FULLNESS if fullness > ZERO else ZERO
            )

            rate_energy = NORMAL_ENERGY

            if satisfaction <= ZERO:
                rate_energy -= Decimal("1")

            if fullness <= ZERO:
                rate_energy -= Decimal("2")

            # 成長速度を判定
            if (
                satisfaction < Decimal("30")
                or energy < Decimal("30")
                or fullness < Decimal("30")
            ):
                rate_growth = LOW_GROWTH
            else:
                rate_growth = NORMAL_GROWTH

            # 各パラメータが境界値に達する時刻を調べる
            candidates = [
                (satisfaction, rate_satisfaction, ZERO),
                (fullness, rate_fullness, ZERO),
                (energy, rate_energy, ZERO),
                (growth, rate_growth, MAX_VALUE),
            ]

            # 成長速度が切り替わる境界も確認
            for value, rate in [
                (satisfaction, rate_satisfaction),
                (energy, rate_energy),
                (fullness, rate_fullness),
            ]:
                if value >= Decimal("30") and rate < ZERO:
                    candidates.append(
                        (value, rate, Decimal("29.9999"))
                    )

            for value, rate, threshold in candidates:

                seconds = time_until_threshold(
                    value, rate, threshold
                )

                if seconds is None:
                    continue

                event_at = cursor + seconds_to_timedelta(seconds)

                if event_at <= cursor:
                    event_at = cursor + timedelta(microseconds=1)
                if event_at < boundary:
                    boundary = event_at

            hours = hours_between(cursor, boundary)

            satisfaction = clamp(
                satisfaction + rate_satisfaction * hours
            )

            fullness = clamp(
                fullness + rate_fullness * hours
            )

            energy = clamp(
                energy + rate_energy * hours
            )

            growth_increase = rate_growth * hours

            old_growth = growth
            growth = clamp(growth + growth_increase)
            natural_added += growth - old_growth

        # 次の区間へ進む
        cursor = boundary

        if sitter_end is not None and cursor >= sitter_end:
            save_data.satisfaction = satisfaction.quantize(PRECISION)
            save_data.energy = energy.quantize(PRECISION)
            save_data.fullness = fullness.quantize(PRECISION)
            save_data.growth = growth.quantize(PRECISION)
            finish_sitter(save_data, sitter_end, auto=True)

        # -------------------------
        # ゲームオーバー判定
        # -------------------------
        if energy <= ZERO:

            save_data.status = "game_over"
            save_data.game_over_at = cursor
            save_data.game_over_count += 1
            break

        # -------------------------
        # クリア判定
        # -------------------------
        if growth >= MAX_VALUE:

            save_data.status = "cleared"
            save_data.cleared_at = cursor
            save_data.clear_count += 1
            break

    # =========================
    # 計算結果を保存
    # =========================

    save_data.satisfaction = satisfaction.quantize(PRECISION)
    save_data.energy = energy.quantize(PRECISION)
    save_data.fullness = fullness.quantize(PRECISION)
    save_data.growth = growth.quantize(PRECISION)

    save_data.natural_growth_total = (
        Decimal(save_data.natural_growth_total) + natural_added
    ).quantize(PRECISION)

    save_data.last_updated_at = cursor

    # =========================
    # ストックの回復
    # =========================

    # 育成終了時刻までの回復を反映する
    final_status = save_data.status

    save_data.status = "playing"

    recover_stocks(save_data, now=cursor)

    save_data.status = final_status

    if save_data.play_started_at and save_data.status == "cleared":
        save_data.clear_time_seconds = max(
            0,
            int((cursor - save_data.play_started_at).total_seconds())
        )

    save_data.save()


    # =========================
    # 自然成長によるクリア記録
    # =========================
    if save_data.status == "cleared":

        elapsed_seconds = 0

        if save_data.play_started_at:
            elapsed_seconds = max(
                0,
                int(
                    (
                        save_data.cleared_at
                        - save_data.play_started_at
                    ).total_seconds()
                )
            )

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
                    extend_to_end=False,
                ),
                "elapsed_seconds": elapsed_seconds,
                "natural_growth_total": save_data.natural_growth_total,
                "active_growth_total": save_data.active_growth_total,
                "sitter_seconds": save_data.sitter_total_seconds,
            }
        )


    # 自然成長・時間経過をログに記録
    RealTimeActionLog.objects.create(
        user=save_data.user,
        game_round=save_data.game_round,
        action="time_update",
        timestamp=cursor,
        satisfaction=save_data.satisfaction,
        energy=save_data.energy,
        fullness=save_data.fullness,
        growth=save_data.growth,
        result=save_data.status,
        growth_delta=natural_added,
        natural_growth_delta=natural_added,
        elapsed_seconds=max(
            0, int((cursor - start).total_seconds())
        ),
    )

    return save_data



@transaction.atomic
def change_bedtime(save_data, new_bedtime, now=None):
    """
    入眠時刻を変更する。

    変更前までの時間は古い設定で計算し、
    変更後は新しい設定を適用する。
    """

    if now is None:
        now = timezone.now()

    # 同時操作によるデータの重複更新を防止
    save_data = (
        RealTimeSaveData.objects
        .select_for_update()
        .get(pk=save_data.pk)
    )

    # 新しい入眠時刻が正しい形式か確認
    if not isinstance(new_bedtime, time):
        raise ValueError("入眠時刻の形式が正しくありません")

    # 変更前の設定で現在までの時間を計算
    save_data = apply_elapsed_time(
        save_data,
        now=now
    )

    # 育成終了後は設定を変更しない
    if save_data.status != "playing":
        return save_data

    # 通常育成中のみ変更できる
    if save_data.tutorial_step != 4:
        return save_data

    old_bedtime = save_data.bedtime

    # 同じ時刻なら変更ログを作成しない
    if old_bedtime == new_bedtime:
        return save_data

    # 新しい入眠時刻を保存
    save_data.bedtime = new_bedtime

    save_data.save(
        update_fields=["bedtime"]
    )

    # 入眠時刻の変更を行動ログに記録
    RealTimeActionLog.objects.create(
        user=save_data.user,
        game_round=save_data.game_round,
        action="change_bedtime",
        timestamp=now,
        satisfaction=save_data.satisfaction,
        energy=save_data.energy,
        fullness=save_data.fullness,
        growth=save_data.growth,
        result=(
            f"{old_bedtime:%H:%M}"
            f" → {new_bedtime:%H:%M}"
        ),
        growth_delta=Decimal("0"),
        natural_growth_delta=Decimal("0"),
        elapsed_seconds=0,
    )

    return save_data


@transaction.atomic
def start_sitter(save_data, now=None):
    """預け入れ。戻り値は（最新育成データ, 成功, メッセージ）。"""
    now = now or timezone.now()
    save_data = apply_elapsed_time(save_data, now)
    local = timezone.localtime(now)
    if save_data.status != "playing" or now < save_data.last_updated_at:
        return save_data, False, "現在は預けられません"

    # 通常育成中のみ利用できる
    if save_data.tutorial_step != 4:
        return save_data, False, "チュートリアル終了後に利用できます"

    if not time(6, 0) <= local.time() < time(19, 0):
        return save_data, False, "利用可能時間は6時から19時までです"
    if save_data.sitter_started_at is not None or save_data.sitter_last_used_date == local.date():
        return save_data, False, "本日は既に利用しています"
    save_data.sitter_started_at = now
    save_data.sitter_last_used_date = local.date()
    save_data.save(update_fields=["sitter_started_at", "sitter_last_used_date"])
    RealTimeSitterLog.objects.create(user=save_data.user, game_round=save_data.game_round, started_at=now)
    record_sitter_action(save_data, "sitter_start", now, "預け入れ")
    return save_data, True, "預け入れました"


@transaction.atomic
def end_sitter(save_data, now=None):
    """途中のお迎え。19時以降は時間更新時に自動終了する。"""
    now = now or timezone.now()
    save_data = apply_elapsed_time(save_data, now)
    if save_data.sitter_started_at is None or now < save_data.last_updated_at:
        return save_data, False, "現在は預けていません"
    finish_sitter(save_data, now)
    return save_data, True, "お迎えしました"
