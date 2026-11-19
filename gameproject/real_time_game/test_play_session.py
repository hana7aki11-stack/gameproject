from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from play_session_system import (
    touch_play_session,
    close_play_session,
    calculate_play_seconds_until,
)

from .models import (
    RealTimeSaveData,
    RealTimePlaySession,
)


class PlaySessionTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="play_session_test",
            password="TestPassword123!"
        )

        self.save_data = RealTimeSaveData.objects.create(
            user=self.user
        )

        self.start = timezone.now()

    # ==========================================
    # テスト用の定期通信
    # ==========================================

    def heartbeat(self, seconds=0, page_view=False,
                  expected_round=None):

        return touch_play_session(
            user=self.user,
            save_model=RealTimeSaveData,
            session_model=RealTimePlaySession,
            page_view=page_view,
            now=self.start + timedelta(seconds=seconds),
            expected_round=expected_round,
        )

    # ==========================================
    # テスト用の終了通信
    # ==========================================

    def end_session(self, seconds, session_id=None):

        close_play_session(
            user=self.user,
            save_model=RealTimeSaveData,
            session_model=RealTimePlaySession,
            session_id=session_id,
            now=self.start + timedelta(seconds=seconds),
        )

    # ==========================================
    # 1. プレイ開始
    # ==========================================

    def test_start_session(self):

        session = self.heartbeat(page_view=True)

        self.save_data.refresh_from_db()

        self.assertEqual(session.started_at, self.start)
        self.assertEqual(session.last_seen_at, self.start)
        self.assertEqual(session.page_views, 1)
        self.assertEqual(self.save_data.play_session_count, 1)
        self.assertEqual(self.save_data.round_play_seconds, 0)

    # ==========================================
    # 2. 定期通信による時間加算
    # ==========================================

    def test_heartbeat_adds_play_time(self):

        first = self.heartbeat()
        second = self.heartbeat(seconds=30)
        third = self.heartbeat(seconds=60)

        self.save_data.refresh_from_db()

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.pk, third.pk)
        self.assertEqual(self.save_data.round_play_seconds, 60)
        self.assertEqual(self.save_data.play_session_count, 1)

    # ==========================================
    # 3. ゲーム内の画面移動
    # ==========================================

    def test_internal_navigation(self):

        first = self.heartbeat(page_view=True)

        second = self.heartbeat(
            seconds=10,
            page_view=True
        )

        self.save_data.refresh_from_db()

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.page_views, 2)
        self.assertEqual(self.save_data.round_play_seconds, 10)
        self.assertEqual(self.save_data.play_session_count, 1)

    # ==========================================
    # 4. プレイ終了
    # ==========================================

    def test_close_session(self):

        session = self.heartbeat()

        self.heartbeat(seconds=30)

        self.end_session(
            seconds=45,
            session_id=session.pk
        )

        session.refresh_from_db()
        self.save_data.refresh_from_db()

        self.assertEqual(
            session.logged_out_at,
            self.start + timedelta(seconds=45)
        )

        self.assertEqual(session.duration_seconds(), 45)
        self.assertEqual(self.save_data.round_play_seconds, 45)

    # ==========================================
    # 5. 終了後の再アクセス
    # ==========================================

    def test_reopen_creates_new_session(self):

        first = self.heartbeat()

        self.end_session(
            seconds=20,
            session_id=first.pk
        )

        second = self.heartbeat(seconds=25)

        self.save_data.refresh_from_db()

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(self.save_data.play_session_count, 2)
        self.assertEqual(self.save_data.round_play_seconds, 20)

    # ==========================================
    # 6. 長時間の通信途絶
    # ==========================================

    def test_long_gap_creates_new_session(self):
        first = self.heartbeat()

        self.heartbeat(seconds=30)

        second = self.heartbeat(seconds=120)

        first.refresh_from_db()
        self.save_data.refresh_from_db()

        self.assertNotEqual(first.pk, second.pk)

        self.assertEqual(
            first.logged_out_at,
            self.start + timedelta(seconds=30)
        )

        self.assertEqual(first.duration_seconds(), 30)
        self.assertIsNone(second.logged_out_at)

        self.assertEqual(self.save_data.play_session_count, 2)
        self.assertEqual(self.save_data.round_play_seconds, 30)

    # ==========================================
    # 7. 長時間通信がない場合の終了
    # ==========================================

    def test_close_after_long_gap(self):

        session = self.heartbeat()

        self.heartbeat(seconds=30)

        self.end_session(
            seconds=300,
            session_id=session.pk
        )

        session.refresh_from_db()
        self.save_data.refresh_from_db()

        self.assertEqual(
            session.logged_out_at,
            self.start + timedelta(seconds=30)
        )

        self.assertEqual(self.save_data.round_play_seconds, 30)

    # ==========================================
    # 8. 終了通信の重複防止
    # ==========================================

    def test_duplicate_close(self):

        session = self.heartbeat()

        self.end_session(
            seconds=20,
            session_id=session.pk
        )

        self.end_session(
            seconds=25,
            session_id=session.pk
        )

        self.save_data.refresh_from_db()

        self.assertEqual(self.save_data.round_play_seconds, 20)

    # ==========================================
    # 9. 前回の育成からの通信を拒否
    # ==========================================

    def test_old_round_heartbeat_is_rejected(self):

        self.save_data.game_round = 2

        self.save_data.save(
            update_fields=["game_round"]
        )

        session = self.heartbeat(
            expected_round=1
        )

        self.assertIsNone(session)

        self.assertEqual(
            RealTimePlaySession.objects.filter(
                user=self.user
            ).count(),
            0
        )

    # ==========================================
    # 10. 育成回数ごとに記録を分ける
    # ==========================================

    def test_new_round_creates_new_session(self):
        first = self.heartbeat(expected_round=1)

        self.heartbeat(
            seconds=20,
            expected_round=1
        )

        self.save_data.game_round = 2
        self.save_data.round_play_seconds = 0

        self.save_data.save(
            update_fields=[
                "game_round",
                "round_play_seconds",
            ]
        )

        second = self.heartbeat(
            seconds=30,
            expected_round=2
        )

        first.refresh_from_db()
        self.save_data.refresh_from_db()

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(first.game_round, 1)
        self.assertEqual(second.game_round, 2)

        self.assertEqual(
            first.logged_out_at,
            self.start + timedelta(seconds=20)
        )

        self.assertEqual(first.duration_seconds(), 20)
        self.assertEqual(self.save_data.round_play_seconds, 0)

        self.assertEqual(
            RealTimePlaySession.objects.filter(
                user=self.user
            ).count(),
            2
        )

    # ==========================================
    # 11. クリア後の時間を除外
    # ==========================================

    def test_calculate_until_clear(self):

        self.heartbeat()

        self.heartbeat(seconds=30)
        self.heartbeat(seconds=60)

        seconds = calculate_play_seconds_until(
            user=self.user,
            session_model=RealTimePlaySession,
            game_round=1,
            ended_at=self.start + timedelta(seconds=45),
        )

        self.assertEqual(seconds, 45)

    # ==========================================
    # 12. ゲームを閉じている間の時間を除外
    # ==========================================

    def test_offline_time_is_excluded(self):

        session = self.heartbeat()

        self.heartbeat(seconds=30)

        self.end_session(
            seconds=40,
            session_id=session.pk
        )

        seconds = calculate_play_seconds_until(
            user=self.user,
            session_model=RealTimePlaySession,
            game_round=1,
            ended_at=self.start + timedelta(hours=3),
        )

        self.assertEqual(seconds, 40)

    # ==========================================
    # 13. 行動によるクリア時刻まで計測
    # ==========================================

    def test_action_clear_extends_play_time(self):

        self.heartbeat()

        self.heartbeat(seconds=30)

        seconds = calculate_play_seconds_until(
            user=self.user,
            session_model=RealTimePlaySession,
            game_round=1,
            ended_at=self.start + timedelta(seconds=45),
        )

        self.assertEqual(seconds, 45)

    # ==========================================
    # 14. 自然成長時は未確認時間を除外
    # ==========================================

    def test_natural_clear_excludes_unconfirmed_time(self):

        self.heartbeat()

        self.heartbeat(seconds=30)

        seconds = calculate_play_seconds_until(
            user=self.user,
            session_model=RealTimePlaySession,
            game_round=1,
            ended_at=self.start + timedelta(seconds=45),
            extend_to_end=False,
        )

        self.assertEqual(seconds, 30)

    # ==========================================
    # 15. 自然成長によるクリア後の時間を除外
    # ==========================================

    def test_natural_clear_excludes_post_clear_time(self):

        self.heartbeat()

        self.heartbeat(seconds=30)
        self.heartbeat(seconds=60)

        seconds = calculate_play_seconds_until(
            user=self.user,
            session_model=RealTimePlaySession,
            game_round=1,
            ended_at=self.start + timedelta(seconds=45),
            extend_to_end=False,
        )

        self.assertEqual(seconds, 45)

    # ==========================================
    # 16. 行動によるクリアでも長時間の通信途絶は除外
    # ==========================================

    def test_action_clear_after_long_gap(self):

        self.heartbeat()

        self.heartbeat(seconds=30)

        seconds = calculate_play_seconds_until(
            user=self.user,
            session_model=RealTimePlaySession,
            game_round=1,
            ended_at=self.start + timedelta(seconds=120),
        )

        self.assertEqual(seconds, 30)