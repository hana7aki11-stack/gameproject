
from django.db import transaction
from django.utils import timezone


# 定期通信の間隔（秒）
HEARTBEAT_SECONDS = 30

# 別のプレイと判定する通信間隔（秒）
SESSION_GAP_SECONDS = 60


# ==========================================
# プレイの開始・継続
# ==========================================

@transaction.atomic
def touch_play_session(
        user,
        save_model,
        session_model,
        page_view=False,
        now=None,
        expected_round=None
):

    if not user.is_authenticated:
        return None

    save_data, _ = (
        save_model.objects
        .select_for_update()
        .get_or_create(user=user)
    )

    now = now or timezone.now()

    game_round = save_data.game_round

    # 前回の育成画面から届いた通信は記録しない
    if (
        expected_round is not None
        and expected_round != game_round
    ):
        return None

    last = (
        session_model.objects
        .filter(user=user)
        .order_by("-started_at", "-pk")
        .first()
    )

    # 同じプレイを継続できるか確認
    if last is not None:

        gap = (
            now - last.last_seen_at
        ).total_seconds()

        if (
            last.logged_out_at is None
            and last.game_round == game_round
            and 0 <= gap <= SESSION_GAP_SECONDS
        ):

            before = last.duration_seconds()

            last.last_seen_at = now

            if page_view:
                last.page_views += 1

            last.save(
                update_fields=[
                    "last_seen_at",
                    "page_views",
                ]
            )

            after = last.duration_seconds()

            save_data.round_play_seconds += max(
                0, after - before
            )

            save_data.save(
                update_fields=[
                    "round_play_seconds",
                ]
            )

            return last

    # 継続できなかった過去のプレイを終了する
    unfinished_sessions = session_model.objects.filter(
            user=user,
            logged_out_at__isnull=True,
    )

    for unfinished in unfinished_sessions:
            unfinished.logged_out_at = unfinished.last_seen_at

            unfinished.save(
                update_fields=["logged_out_at"]
            )

    # 新しいプレイとして記録
    new_session = session_model.objects.create(
        user=user,
        game_round=game_round,
        started_at=now,
        last_seen_at=now,
        page_views=1 if page_view else 0,
    )

    save_data.play_session_count += 1

    save_data.save(
        update_fields=[
            "play_session_count",
        ]
    )

    return new_session


# ==========================================
# プレイ終了
# ==========================================

@transaction.atomic
def close_play_session(
    user,
    save_model,
    session_model,
    session_id=None,
    is_logout=False,
    now=None,
):

    if not user.is_authenticated:
        return

    save_data = (
        save_model.objects
        .select_for_update()
        .filter(user=user)
        .first()
    )

    if save_data is None:
        return

    now = now or timezone.now()

    sessions = session_model.objects.filter(
        user=user,
        game_round=save_data.game_round,
        logged_out_at__isnull=True,
    )

    if session_id is not None:
        sessions = sessions.filter(
            pk=session_id
        )

    last = (
        sessions
        .order_by("-started_at", "-pk")
        .first()
    )

    if last is None:
        return

    before = last.duration_seconds()

    gap = (
        now - last.last_seen_at
    ).total_seconds()

    # 通信が継続していれば終了時刻まで計測
    if 0 <= gap <= SESSION_GAP_SECONDS:
        end = now
    else:
        # 長時間通信がなければ最終通信時刻を使用
        end = last.last_seen_at

    last.last_seen_at = end

    # セッションの終了を記録
    last.logged_out_at = end

    last.save(
        update_fields=[
            "last_seen_at",
            "logged_out_at",
        ]
    )

    after = last.duration_seconds()

    save_data.round_play_seconds += max(
        0, after - before
    )

    save_data.save(
        update_fields=[
            "round_play_seconds",
        ]
    )


# ==========================================
# 指定時刻までの累積プレイ時間
# ==========================================

def calculate_play_seconds_until(
        user,
        session_model,
        game_round,
        ended_at,
        *,
        extend_to_end=True
):

    sessions = session_model.objects.filter(
        user=user,
        game_round=game_round,
        started_at__lte=ended_at,
    )

    total_seconds = 0

    for session in sessions:

        # 記録済みのプレイ終了時刻
        session_end = (
            session.logged_out_at
            or session.last_seen_at
        )

        # 行動によるクリアの場合のみ、
        # 最終通信から60秒以内ならクリア時刻まで計測
        if (
                extend_to_end
                and session.logged_out_at is None
                and 0 <= (
                    ended_at - session.last_seen_at
                ).total_seconds() <= SESSION_GAP_SECONDS
        ):

                session_end = ended_at

        # クリア後の時間は含めない
        session_end = min(
            session_end,
            ended_at
        )

        total_seconds += max(
            0,
            int(
                (
                    session_end
                    - session.started_at
                ).total_seconds()
            )
        )

    return total_seconds
