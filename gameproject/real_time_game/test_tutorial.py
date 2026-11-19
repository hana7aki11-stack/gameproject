from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from .models import (
    RealTimeSaveData,
    RealTimeActionLog,
    RealTimeMinigameSession,
)

from .time_system import (
    change_bedtime,
    start_sitter,
    apply_elapsed_time,
)


class TutorialTests(TestCase):

    def setUp(self):

        self.now = datetime(
            2026, 11, 17, 12, 0,
            tzinfo=ZoneInfo("Asia/Tokyo")
        )

        self.user = User.objects.create_user(
            username="tutorial_test",
            password="testpassword123"
        )

        self.client.force_login(self.user)

        self.save_data = RealTimeSaveData.objects.create(
            user=self.user,
            status="playing",
            has_started_game=True,
            tutorial_step=1,
            game_round=1,
            play_started_at=self.now,
            last_updated_at=self.now,
        )

    # =========================
    # イントロ終了
    # =========================

    def test_finish_intro(self):

        self.save_data.tutorial_step = 0
        self.save_data.save()

        with patch(
            "real_time_game.views.timezone.now",
            return_value=self.now
        ):
            response = self.client.post(
                reverse("real_time_game:finish_intro"),
                {"game_round": 1}
            )

        self.assertEqual(response.status_code, 302)

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.tutorial_step, 1
        )
        self.assertEqual(
            self.save_data.fullness, 25
        )

        self.assertTrue(
            RealTimeActionLog.objects.filter(
                user=self.user,
                action="intro_finish"
            ).exists()
        )

    # =========================
    # チュートリアルのスキップ
    # =========================

    def test_skip_tutorial(self):

        self.save_data.fullness = 40
        self.save_data.items = ["plant"]
        self.save_data.save()

        skip_time = self.now + timedelta(hours=2)

        with patch(
            "real_time_game.views.timezone.now",
            return_value=skip_time
        ):
            response = self.client.post(
                reverse("real_time_game:skip_tutorial"),
                {"game_round": 1}
            )

        self.assertEqual(response.status_code, 302)

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.tutorial_step, 5
        )
        self.assertEqual(
            self.save_data.last_updated_at, skip_time
        )
        self.assertEqual(
            self.save_data.fullness, 40
        )
        self.assertEqual(
            self.save_data.stock_food, 2
        )
        self.assertEqual(
            self.save_data.items, ["plant"]
        )

        self.assertEqual(
            RealTimeActionLog.objects.filter(
                user=self.user,
                action="tutorial_skip"
            ).count(), 1
        )

    # 古い育成画面からのスキップを防止
    def test_skip_wrong_round(self):

        self.client.post(
            reverse("real_time_game:skip_tutorial"),
            {"game_round": 999}
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.tutorial_step, 1
        )

    # イントロ中はスキップできない
    def test_skip_during_intro(self):

        self.save_data.tutorial_step = 0
        self.save_data.save()

        self.client.post(
            reverse("real_time_game:skip_tutorial"),
            {"game_round": 1}
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.tutorial_step, 0
        )

    # 二重実行の防止
    def test_skip_twice(self):

        for _ in range(2):
            self.client.post(
                reverse("real_time_game:skip_tutorial"),
                {"game_round": 1}
            )

        self.assertEqual(
            RealTimeActionLog.objects.filter(
                user=self.user,
                action="tutorial_skip"
            ).count(), 1
        )

    # ミニゲーム中はスキップできない
    def test_skip_during_minigame(self):

        RealTimeMinigameSession.objects.create(
            user=self.user,
            game_round=1,
            action="food",
            difficulty="easy",
            status="playing",
            started_at=self.now,
            is_tutorial=True,
            stock_consumed=False,
        )

        with patch(
            "real_time_game.views.timezone.now",
            return_value=self.now
        ):
            self.client.post(
                reverse("real_time_game:skip_tutorial"),
                {"game_round": 1}
            )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.tutorial_step, 1
        )

    # =========================
    # 就寝時刻の変更制限
    # =========================

    def test_bedtime_restriction(self):

        original_bedtime = self.save_data.bedtime

        change_bedtime(
            self.save_data,
            time(20, 0),
            now=self.now
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.bedtime,
            original_bedtime
        )

        self.assertFalse(
            RealTimeActionLog.objects.filter(
                user=self.user,
                action="change_bedtime"
            ).exists()
        )

    # =========================
    # シッターの利用制限
    # =========================

    def test_sitter_restriction(self):

        save, success, message = start_sitter(
            self.save_data,
            now=self.now
        )

        self.assertFalse(success)

        self.save_data.refresh_from_db()

        self.assertIsNone(
            self.save_data.sitter_started_at
        )
        self.assertIsNone(
            self.save_data.sitter_last_used_date
        )

    # =========================
    # 家具の操作制限
    # =========================

    def test_furniture_restriction(self):

        self.save_data.items = ["plant"]
        self.save_data.save()

        self.client.post(
            reverse("real_time_game:manage_item"),
            {
                "operation": "place",
                "item": "plant",
            }
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.placed_items, []
        )
        self.assertEqual(
            self.save_data.items, ["plant"]
        )


    # =========================
    # 追加説明中は時間経過を停止
    # =========================

    def test_extra_intro_freeze(self):

        self.save_data.tutorial_step = 5
        self.save_data.save()

        later = self.now + timedelta(hours=3)

        save = apply_elapsed_time(
            self.save_data,
            now=later
        )

        self.assertEqual(save.satisfaction, 50)
        self.assertEqual(save.energy, 50)
        self.assertEqual(save.fullness, 50)
        self.assertEqual(save.growth, 0)
        self.assertEqual(save.stock_food, 2)
        self.assertEqual(save.last_updated_at, later)


    # =========================
    # 追加説明の終了
    # =========================

    def test_finish_extra_intro(self):

        self.save_data.tutorial_step = 5
        self.save_data.save()

        finish_time = self.now + timedelta(hours=2)

        with patch(
            "real_time_game.views.timezone.now",
            return_value=finish_time
        ):

            response = self.client.post(
                reverse("real_time_game:finish_extra_intro"),
                {"game_round": 1}
            )

        self.assertEqual(response.status_code, 302)

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.tutorial_step, 4
        )

        self.assertEqual(
            self.save_data.last_updated_at,
            finish_time
        )

        self.assertEqual(self.save_data.growth, 0)

        self.assertEqual(
            RealTimeActionLog.objects.filter(
                user=self.user,
                action="extra_intro_finish"
            ).count(), 1
        )

        # 終了後は時間経過が再開する
        save = apply_elapsed_time(
            self.save_data,
            now=finish_time + timedelta(hours=1)
        )

        self.assertGreater(save.growth, 0)
        self.assertLess(save.fullness, 50)


    # =========================
    # 古い育成画面からの操作を防止
    # =========================

    def test_extra_intro_wrong_round(self):

        self.save_data.tutorial_step = 5
        self.save_data.save()

        self.client.post(
            reverse("real_time_game:finish_extra_intro"),
            {"game_round": 999}
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.tutorial_step, 5
        )


    # =========================
    # 二重終了を防止
    # =========================

    def test_extra_intro_finish_twice(self):

        self.save_data.tutorial_step = 5
        self.save_data.save()

        with patch(
            "real_time_game.views.timezone.now",
            return_value=self.now
        ):

            for _ in range(2):

                self.client.post(
                    reverse("real_time_game:finish_extra_intro"),
                    {"game_round": 1}
                )

        self.assertEqual(
            RealTimeActionLog.objects.filter(
                user=self.user,
                action="extra_intro_finish"
            ).count(), 1
        )


    # =========================
    # 追加説明中の操作制限
    # =========================

    def test_extra_intro_restrictions(self):

        self.save_data.tutorial_step = 5
        self.save_data.items = ["plant"]
        self.save_data.save()

        original_bedtime = self.save_data.bedtime

        change_bedtime(
            self.save_data,
            time(20, 0),
            now=self.now
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.bedtime,
            original_bedtime
        )

        save, success, message = start_sitter(
            self.save_data,
            now=self.now
        )

        self.assertFalse(success)

        self.client.post(
            reverse("real_time_game:manage_item"),
            {
                "operation": "place",
                "item": "plant",
            }
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.placed_items, []
        )

        self.assertIsNone(
            self.save_data.sitter_started_at
        )