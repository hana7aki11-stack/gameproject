
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    RealTimeSaveData,
    RealTimeActionLog,
    RealTimeClearLog,
)

from .action_system import apply_action
from .time_system import start_sitter


JST = ZoneInfo("Asia/Tokyo")


class ActionIntegrationTests(TestCase):

    def setUp(self):

        self.user = (
            get_user_model().objects.create_user(
                username="action_test_user",
                password="test-password"
            )
        )

        self.start = datetime(
            2026, 11, 17, 10, 0,
            tzinfo=JST
        )

        self.save_data = (
            RealTimeSaveData.objects.create(
                user=self.user,
                status="playing",
                has_started_game=True,
                play_started_at=self.start,
                last_updated_at=self.start,
                tutorial_step=4,
            )
        )

    # =========================
    # 基本報酬・ストック・保存
    # =========================

    def test_food_action(self):

        save, success, info = apply_action(
            self.save_data,
            "food",
            lives=3,
            now=self.start
        )

        self.assertTrue(success)

        save.refresh_from_db()

        self.assertEqual(save.satisfaction, 70)
        self.assertEqual(save.energy, 55)
        self.assertEqual(save.fullness, 80)

        self.assertEqual(
            save.growth,
            Decimal("2.4")
        )

        self.assertEqual(save.stock_food, 1)

        self.assertEqual(
            save.active_growth_total,
            Decimal("2.4")
        )

    # =========================
    # 行動回数
    # =========================

    def test_action_counters(self):

        save, success, info = apply_action(
            self.save_data,
            "food",
            lives=3,
            now=self.start
        )

        save.refresh_from_db()

        self.assertEqual(
            save.action_food_count, 1
        )

        self.assertEqual(
            save.minigame_food_play, 1
        )

        self.assertEqual(
            save.minigame_food_success, 1
        )

        self.assertEqual(
            save.healthy_food_count, 1
        )

    # =========================
    # ストック不足
    # =========================

    def test_empty_stock(self):

        self.save_data.stock_food = 0
        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "food",
            lives=3,
            now=self.start
        )

        self.assertFalse(success)

        self.assertEqual(save.growth, 0)

        self.assertEqual(
            save.action_food_count, 0
        )

    # =========================
    # 睡眠中の操作
    # =========================

    def test_sleep_restriction(self):

        now = self.start.replace(hour=23)

        self.save_data.last_updated_at = now
        self.save_data.play_started_at = now

        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "rest",
            now=now
        )

        self.assertFalse(success)
        self.assertEqual(save.stock_rest, 2)

    # =========================
    # シッター利用中
    # =========================

    def test_sitter_restriction(self):

        save, success, message = start_sitter(
            self.save_data,
            now=self.start
        )

        self.assertTrue(success)

        save, success, info = apply_action(
            save,
            "rest",
            now=self.start
        )

        self.assertFalse(success)
        self.assertEqual(save.stock_rest, 2)

    # =========================
    # 良い状態ボーナス+1
    # =========================

    def test_good_bonus_one(self):

        self.save_data.satisfaction = 80
        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "ball",
            score=10,
            now=self.start
        )

        self.assertEqual(
            info["good_bonus"], 1
        )

        self.assertEqual(
            save.growth,
            Decimal("3.4")
        )

    # =========================
    # 良い状態ボーナス+2
    # =========================

    def test_good_bonus_two(self):

        self.save_data.satisfaction = 80
        self.save_data.energy = 90

        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "ball",
            score=10,
            now=self.start
        )

        self.assertEqual(
            info["good_bonus"], 2
        )

        self.assertEqual(
            save.growth,
            Decimal("4.4")
        )

    # =========================
    # 3時間以内は再獲得不可
    # =========================

    def test_good_bonus_cooldown(self):

        self.save_data.satisfaction = 80

        self.save_data.last_good_bonus_at = (
            self.start - timedelta(hours=2)
        )

        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "ball",
            score=10,
            now=self.start
        )

        self.assertEqual(
            info["good_bonus"], 0
        )

    # =========================
    # 3時間後は再獲得可能
    # =========================

    def test_good_bonus_recovery(self):

        self.save_data.satisfaction = 80

        self.save_data.last_good_bonus_at = (
            self.start - timedelta(hours=3)
        )

        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "ball",
            score=10,
            now=self.start
        )

        self.assertEqual(
            info["good_bonus"], 1
        )

    # =========================
    # 低体力時のペナルティ
    # =========================

    def test_low_energy_penalty(self):

        self.save_data.energy = 35
        self.save_data.growth = 10

        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "ball",
            score=10,
            now=self.start
        )

        self.assertEqual(save.energy, 15)

        self.assertEqual(
            save.growth,
            Decimal("10.4")
        )

    # =========================
    # 家具の保存
    # =========================

    @patch(
        "real_time_game.action_system.draw_item",
        return_value="sofa"
    )
    def test_item_saved(self, mock_draw):

        self.save_data.satisfaction = 80
        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "ball",
            score=10,
            now=self.start
        )

        save.refresh_from_db()

        self.assertIn("sofa", save.items)
        self.assertIn("sofa", save.new_items)

    # =========================
    # 行動ログ
    # =========================

    def test_action_log(self):

        save, success, info = apply_action(
            self.save_data,
            "food",
            lives=3,
            now=self.start
        )

        log = RealTimeActionLog.objects.get(
            user=self.user,
            action="好きなごはん選び"
        )

        self.assertEqual(
            log.growth_delta,
            Decimal("2.4")
        )

        self.assertEqual(
            log.natural_growth_delta, 0
        )

        self.assertIn(
            "ライフ:3", log.result
        )

    # =========================
    # 行動によるクリア
    # =========================

    def test_action_clear(self):

        self.save_data.growth = 99

        self.save_data.active_growth_total = 60
        self.save_data.natural_growth_total = 39

        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "ball",
            score=15,
            now=self.start
        )

        save.refresh_from_db()

        self.assertEqual(
            save.status, "cleared"
        )

        self.assertEqual(save.growth, 100)
        self.assertEqual(save.clear_count, 1)

        log = RealTimeClearLog.objects.get(
            user=self.user
        )

        self.assertEqual(
            log.active_growth_total, 61
        )

        self.assertEqual(
            log.natural_growth_total, 39
        )

        # 終了後の再操作を拒否する
        save, success, info = apply_action(
            save,
            "ball",
            score=15,
            now=self.start
        )

        self.assertFalse(success)

        self.assertEqual(
            RealTimeClearLog.objects.filter(
                user=self.user
            ).count(),
            1
        )

    # =========================
    # 行動によるゲームオーバー
    # =========================

    def test_action_game_over(self):

        self.save_data.energy = 15
        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "ball",
            score=0,
            now=self.start
        )

        save.refresh_from_db()

        self.assertEqual(save.energy, 0)

        self.assertEqual(
            save.status, "game_over"
        )

        self.assertEqual(
            save.game_over_count, 1
        )

    # =========================
    # 未解放の難易度
    # =========================

    def test_locked_difficulty(self):

        save, success, info = apply_action(
            self.save_data,
            "dance",
            result="clear",
            difficulty="oni",
            now=self.start
        )

        self.assertFalse(success)

        self.assertEqual(
            save.stock_dance, 2
        )

    # =========================
    # チュートリアル中のストック
    # =========================

    def test_tutorial_stock(self):

        self.save_data.tutorial_step = 1
        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "food",
            lives=2,
            now=self.start
        )

        self.assertTrue(success)

        self.assertEqual(
            save.stock_food, 2
        )

        log = RealTimeActionLog.objects.get(
            user=self.user,
            action="好きなごはん選び"
        )

        self.assertIn(
            "[練習]", log.result
        )
