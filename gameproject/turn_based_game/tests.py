from datetime import timedelta

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from .models import SaveData, PlaySession

from play_session_system import (
    touch_play_session,
    close_play_session,
    calculate_play_seconds_until,
)


class PlaySessionTests(TestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username="turn_play_session_test",
            password="TestPassword123!"
        )

        self.save_data = SaveData.objects.create(
            user=self.user
        )

        self.start = timezone.now()

    # ==================================================
    # 共通処理
    # ==================================================

    def heartbeat(
        self,
        seconds=0,
        page_view=False,
        expected_round=None
    ):

        return touch_play_session(
            user=self.user,
            save_model=SaveData,
            session_model=PlaySession,
            page_view=page_view,
            expected_round=expected_round,
            now=self.start + timedelta(seconds=seconds)
        )

    def end_session(self, seconds, session_id=None):

        close_play_session(
            user=self.user,
            save_model=SaveData,
            session_model=PlaySession,
            session_id=session_id,
            now=self.start + timedelta(seconds=seconds)
        )

    # ==================================================
    # 1. プレイ開始
    # ==================================================

    def test_start_session(self):

        session = self.heartbeat(
            0,
            page_view=True
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            PlaySession.objects.count(), 1
        )

        self.assertEqual(
            session.started_at, self.start
        )

        self.assertEqual(
            session.page_views, 1
        )

        self.assertEqual(
            self.save_data.play_session_count, 1
        )

    # ==================================================
    # 2. プレイ時間の加算
    # ==================================================

    def test_continuous_play(self):

        self.heartbeat(0)
        self.heartbeat(30)
        self.heartbeat(60)

        self.save_data.refresh_from_db()

        self.assertEqual(
            PlaySession.objects.count(), 1
        )

        self.assertEqual(
            self.save_data.round_play_seconds, 60
        )

    # ==================================================
    # 3. ゲーム内の画面遷移
    # ==================================================

    def test_internal_navigation(self):

        first = self.heartbeat(
            0,
            page_view=True
        )

        second = self.heartbeat(
            10,
            page_view=True
        )

        self.assertEqual(
            first.pk, second.pk
        )

        self.assertEqual(
            second.page_views, 2
        )

        self.assertEqual(
            PlaySession.objects.count(), 1
        )

    # ==================================================
    # 4. プレイ終了
    # ==================================================

    def test_end_session(self):

        session = self.heartbeat(0)

        self.heartbeat(30)

        self.end_session(
            45,
            session.pk
        )

        session.refresh_from_db()
        self.save_data.refresh_from_db()

        self.assertEqual(
            session.logged_out_at,
            self.start + timedelta(seconds=45)
        )

        self.assertEqual(
            session.duration_seconds(), 45
        )

        self.assertEqual(
            self.save_data.round_play_seconds, 45
        )

    # ==================================================
    # 5. プレイ再開
    # ==================================================

    def test_reopen_game(self):

        first = self.heartbeat(0)

        self.end_session(
            20,
            first.pk
        )

        second = self.heartbeat(25)

        self.save_data.refresh_from_db()

        self.assertNotEqual(
            first.pk, second.pk
        )

        self.assertEqual(
            PlaySession.objects.count(), 2
        )

        self.assertEqual(
            self.save_data.play_session_count, 2
        )

    # ==================================================
    # 6. 長時間の通信途絶
    # ==================================================

    def test_long_gap(self):

        first = self.heartbeat(0)

        self.heartbeat(30)

        second = self.heartbeat(120)

        self.save_data.refresh_from_db()

        self.assertNotEqual(
            first.pk, second.pk
        )

        self.assertEqual(
            self.save_data.round_play_seconds, 30
        )

    # ==================================================
    # 7. 遅れて終了通知が届いた場合
    # ==================================================

    def test_delayed_end(self):

        session = self.heartbeat(0)

        self.heartbeat(30)

        self.end_session(
            300,
            session.pk
        )

        session.refresh_from_db()
        self.save_data.refresh_from_db()

        self.assertEqual(
            session.duration_seconds(), 30
        )

        self.assertEqual(
            self.save_data.round_play_seconds, 30
        )

    # ==================================================
    # 8. 終了通知が重複した場合
    # ==================================================

    def test_duplicate_end(self):

        session = self.heartbeat(0)

        self.end_session(20, session.pk)
        self.end_session(25, session.pk)

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.round_play_seconds, 20
        )

    # ==================================================
    # 9. 古い育成回からの通信
    # ==================================================

    def test_old_round_rejected(self):

        old_round = self.save_data.game_round

        self.save_data.game_round += 1

        self.save_data.save(
            update_fields=["game_round"]
        )

        session = self.heartbeat(
            0,
            expected_round=old_round
        )

        self.assertIsNone(session)

        self.assertEqual(
            PlaySession.objects.count(), 0
        )

    # ==================================================
    # 10. 新しい育成回のセッション
    # ==================================================

    def test_new_round_session(self):

        first = self.heartbeat(0)

        self.end_session(
            20,
            first.pk
        )

        self.save_data.refresh_from_db()

        self.save_data.game_round += 1
        self.save_data.round_play_seconds = 0

        self.save_data.save(
            update_fields=[
                "game_round",
                "round_play_seconds"
            ]
        )

        second = self.heartbeat(
            30,
            expected_round=self.save_data.game_round
        )

        self.assertNotEqual(
            first.game_round,
            second.game_round
        )

        self.assertNotEqual(
            first.pk,
            second.pk
        )

    # ==================================================
    # 11. クリア時点までのプレイ時間
    # ==================================================

    def test_play_seconds_until_clear(self):

        self.heartbeat(0)
        self.heartbeat(30)
        self.heartbeat(60)

        seconds = calculate_play_seconds_until(
            user=self.user,
            session_model=PlaySession,
            game_round=self.save_data.game_round,
            ended_at=self.start + timedelta(seconds=45)
        )

        self.assertEqual(seconds, 45)

    # ==================================================
    # 12. プレイ終了後の時間を加算しない
    # ==================================================

    def test_closed_session_until_clear(self):

        session = self.heartbeat(0)

        self.heartbeat(30)

        self.end_session(
            40,
            session.pk
        )

        seconds = calculate_play_seconds_until(
            user=self.user,
            session_model=PlaySession,
            game_round=self.save_data.game_round,
            ended_at=self.start + timedelta(hours=3)
        )

        self.assertEqual(seconds, 40)