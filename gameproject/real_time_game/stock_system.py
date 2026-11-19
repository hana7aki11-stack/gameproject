
from datetime import datetime, timedelta

from django.utils import timezone


# =========================
# ストックの基本設定
# =========================

MAX_STOCK = 2

# 各行動の回復時間（時間単位）
STOCK_RECOVERY_HOURS = {
    "ball": 3,
    "food": 4,
    "dodge": 3,
    "dance": 3,
    "timing": 4,
    "count": 3,
    "rest": 4,
}


# =========================
# ストックの回復処理
# =========================

def recover_stocks(save_data, now=None):
    """
    経過時間に応じてストックを回復する。
    最大ストック数は2。
    """

    if now is None:
        now = timezone.now()

    if save_data.status != "playing":
        return save_data

    recovery_at = dict(save_data.stock_recovery_at)

    for action, hours in STOCK_RECOVERY_HOURS.items():

        field_name = f"stock_{action}"
        stock = getattr(save_data, field_name)

        # 最大数なら回復時刻を削除
        if stock >= MAX_STOCK:

            setattr(save_data, field_name, MAX_STOCK)
            recovery_at.pop(action, None)

            continue

        # 次の回復日時を取得
        next_recovery = recovery_at.get(action)

        if next_recovery:

            next_recovery = datetime.fromisoformat(
                next_recovery
            )

        else:

            next_recovery = now + timedelta(hours=hours)

        # 経過時間に応じて回復
        while (
            stock < MAX_STOCK
            and now >= next_recovery
        ):

            stock += 1

            next_recovery += timedelta(hours=hours)

        setattr(save_data, field_name, stock)

        # 全回復した場合
        if stock >= MAX_STOCK:

            recovery_at.pop(action, None)

        else:

            recovery_at[action] = (
                next_recovery.isoformat()
            )

    save_data.stock_recovery_at = recovery_at

    return save_data


# =========================
# ストックの消費処理
# =========================

def consume_stock(save_data, action, now=None):
    """
    指定した行動のストックを1つ消費する。

    消費できた場合はTrue、
    消費できなかった場合はFalseを返す。
    """

    if now is None:
        now = timezone.now()

    if action not in STOCK_RECOVERY_HOURS:
        return False

    if save_data.status != "playing":
        return False

    # 消費前に回復状況を更新
    recover_stocks(save_data, now)

    field_name = f"stock_{action}"
    stock = getattr(save_data, field_name)

    # ストックがなければ消費不可
    if stock <= 0:
        return False

    recovery_at = dict(save_data.stock_recovery_at)

    # 最大数から消費した場合のみ
    # 新しい回復時間を設定する
    if stock == MAX_STOCK:

        hours = STOCK_RECOVERY_HOURS[action]

        recovery_at[action] = (
            now + timedelta(hours=hours)
        ).isoformat()

    # ストックを1つ消費
    setattr(save_data, field_name, stock - 1)

    save_data.stock_recovery_at = recovery_at

    return True
