
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import RealTimeSaveData

from .stock_system import (
    MAX_STOCK,
    STOCK_RECOVERY_HOURS,
    recover_stocks,
    consume_stock,
)

from .time_system import (
    apply_elapsed_time,
    start_sitter,
)


JST = ZoneInfo("Asia/Tokyo")


class StockSystemTests(TestCase):

    # =========================
    # テスト用データの作成
    # =========================

    def setUp(self):

        self.user = get_user_model().objects.create_user(
            username="stock_test_user",
            password="test-password"
        )

        self.start = datetime(
            2026, 11, 17, 10, 0, tzinfo=JST
        )

        self.save_data = RealTimeSaveData.objects.create(
            user=self.user,
            status="playing",
            has_started_game=True,
            tutorial_step=4,
            play_started_at=self.start,
            last_updated_at=self.start,
        )


    # =========================
    # 初期ストック
    # =========================

    def test_initial_stocks(self):

        for action in STOCK_RECOVERY_HOURS:

            self.assertEqual(
                getattr(self.save_data, f"stock_{action}"),
                MAX_STOCK
            )


    # =========================
    # ストックの消費
    # =========================

    def test_consume_stock(self):

        success = consume_stock(
            self.save_data, "ball", now=self.start
        )

        self.assertTrue(success)
        self.assertEqual(self.save_data.stock_ball, 1)

        self.assertEqual(
            self.save_data.stock_recovery_at["ball"],
            (self.start + timedelta(hours=3)).isoformat()
        )


    # =========================
    # ストック0の場合
    # =========================

    def test_empty_stock(self):

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        success = consume_stock(
            self.save_data, "ball", now=self.start
        )

        self.assertFalse(success)
        self.assertEqual(self.save_data.stock_ball, 0)


    # =========================
    # 3時間で回復する行動
    # =========================

    def test_three_hour_recovery(self):

        for action in ["ball", "dodge", "dance", "count"]:

            consume_stock(
                self.save_data, action, now=self.start
            )

        recover_stocks(
            self.save_data,
            now=self.start + timedelta(hours=2, minutes=59)
        )

        for action in ["ball", "dodge", "dance", "count"]:

            self.assertEqual(
                getattr(self.save_data, f"stock_{action}"),
                1
            )

        recover_stocks(
            self.save_data,
            now=self.start + timedelta(hours=3)
        )

        for action in ["ball", "dodge", "dance", "count"]:

            self.assertEqual(
                getattr(self.save_data, f"stock_{action}"),
                2
            )


    # =========================
    # 4時間で回復する行動
    # =========================

    def test_four_hour_recovery(self):

        for action in ["food", "timing", "rest"]:

            consume_stock(
                self.save_data, action, now=self.start
            )

        recover_stocks(
            self.save_data,
            now=self.start + timedelta(hours=3, minutes=59)
        )

        for action in ["food", "timing", "rest"]:

            self.assertEqual(
                getattr(self.save_data, f"stock_{action}"),
                1
            )

        recover_stocks(
            self.save_data,
            now=self.start + timedelta(hours=4)
        )

        for action in ["food", "timing", "rest"]:

            self.assertEqual(
                getattr(self.save_data, f"stock_{action}"),
                2
            )


    # =========================
    # 連続消費しても回復時刻を維持
    # =========================

    def test_recovery_timer_not_reset(self):

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        original_recovery = (
            self.save_data.stock_recovery_at["ball"]
        )

        consume_stock(
            self.save_data,
            "ball",
            now=self.start + timedelta(hours=1)
        )

        self.assertEqual(
            self.save_data.stock_ball, 0
        )

        self.assertEqual(
            self.save_data.stock_recovery_at["ball"],
            original_recovery
        )

        recover_stocks(
            self.save_data,
            now=self.start + timedelta(hours=3)
        )

        self.assertEqual(self.save_data.stock_ball, 1)

        recover_stocks(
            self.save_data,
            now=self.start + timedelta(hours=6)
        )

        self.assertEqual(self.save_data.stock_ball, 2)


    # =========================
    # 最大ストック数を超えない
    # =========================

    def test_max_stock_limit(self):

        for _ in range(2):

            consume_stock(
                self.save_data, "ball", now=self.start
            )

        recover_stocks(
            self.save_data,
            now=self.start + timedelta(hours=24)
        )

        self.assertEqual(self.save_data.stock_ball, 2)

        self.assertNotIn(
            "ball",
            self.save_data.stock_recovery_at
        )


    # =========================
    # 全回復後の再消費
    # =========================

    def test_consume_after_full_recovery(self):

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        recover_stocks(
            self.save_data,
            now=self.start + timedelta(hours=6)
        )

        new_start = self.start + timedelta(hours=8)

        consume_stock(
            self.save_data, "ball", now=new_start
        )

        self.assertEqual(self.save_data.stock_ball, 1)

        self.assertEqual(
            self.save_data.stock_recovery_at["ball"],
            (new_start + timedelta(hours=3)).isoformat()
        )


    # =========================
    # 睡眠中のストック回復
    # =========================

    def test_recovery_during_sleep(self):

        start = self.start.replace(hour=22)

        self.save_data.bedtime = time(23, 0)

        consume_stock(
            self.save_data, "ball", now=start
        )

        recover_stocks(
            self.save_data,
            now=start + timedelta(hours=3)
        )

        self.assertEqual(self.save_data.stock_ball, 2)


    # =========================
    # シッター利用中のストック回復
    # =========================

    def test_recovery_during_sitter(self):

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        self.save_data.sitter_started_at = self.start

        recover_stocks(
            self.save_data,
            now=self.start + timedelta(hours=3)
        )

        self.assertEqual(self.save_data.stock_ball, 2)


    # =========================
    # 各ストックの独立性
    # =========================

    def test_independent_stocks(self):

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        self.assertEqual(self.save_data.stock_ball, 1)

        for action in STOCK_RECOVERY_HOURS:

            if action != "ball":

                self.assertEqual(
                    getattr(self.save_data, f"stock_{action}"),
                    2
                )


    # =========================
    # 育成終了後は消費・回復しない
    # =========================

    def test_no_stock_changes_after_game_end(self):

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        for status in ["cleared", "game_over"]:

            self.save_data.status = status

            now = self.start + timedelta(hours=6)

            recover_stocks(
                self.save_data, now=now
            )

            self.assertEqual(
                self.save_data.stock_ball, 1
            )

            success = consume_stock(
                self.save_data, "ball", now=now
            )

            self.assertFalse(success)

            self.assertEqual(
                self.save_data.stock_ball, 1
            )


    def test_integrated_stock_recovery(self):
        """時間更新によってストックが回復・保存される"""

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        self.save_data.save()

        apply_elapsed_time(
            self.save_data,
            now=self.start + timedelta(hours=3)
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.stock_ball, 2
        )

        self.assertNotIn(
            "ball",
            self.save_data.stock_recovery_at
        )


    def test_integrated_sleep_recovery(self):
        """実際の睡眠時間中にストックが回復する"""

        start = self.start.replace(hour=22)

        self.save_data.last_updated_at = start
        self.save_data.play_started_at = start
        self.save_data.bedtime = time(23, 0)

        consume_stock(
            self.save_data, "ball", now=start
        )

        self.save_data.save()

        apply_elapsed_time(
            self.save_data,
            now=start + timedelta(hours=3)
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.stock_ball, 2
        )


    def test_integrated_sitter_recovery(self):
        """実際のシッター利用中にも回復する"""

        consume_stock(
            self.save_data, "rest", now=self.start
        )

        self.save_data.save()

        save, success, message = start_sitter(
            self.save_data,
            now=self.start
        )

        self.assertTrue(success)

        apply_elapsed_time(
            save,
            now=self.start + timedelta(hours=4)
        )

        save.refresh_from_db()

        self.assertEqual(save.stock_rest, 2)

        self.assertIsNotNone(
            save.sitter_started_at
        )


    def test_integrated_offline_recovery(self):
        """長時間アクセスしなくても回復が保存される"""

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        self.save_data.energy = 100

        self.save_data.save()

        save, success, message = start_sitter(
            self.save_data,
            now=self.start
        )

        self.assertTrue(success)

        apply_elapsed_time(
            save,
            now=self.start + timedelta(hours=12)
        )

        save.refresh_from_db()

        self.assertEqual(save.stock_ball, 2)


    def test_integrated_recovery_until_game_over(self):
        """ゲームオーバー後の時間では回復しない"""

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        # 1時間後に体力が0になる状態
        self.save_data.energy = 1.5

        self.save_data.save()

        apply_elapsed_time(
            self.save_data,
            now=self.start + timedelta(hours=6)
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.status,
            "game_over"
        )

        # 回復には3時間必要なので回復しない
        self.assertEqual(
            self.save_data.stock_ball, 1
        )


    def test_integrated_repeated_update(self):
        """同じ時刻で更新しても二重回復しない"""

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        consume_stock(
            self.save_data, "ball", now=self.start
        )

        self.save_data.save()

        end = self.start + timedelta(hours=3)

        apply_elapsed_time(
            self.save_data, now=end
        )

        apply_elapsed_time(
            self.save_data, now=end
        )

        self.save_data.refresh_from_db()

        self.assertEqual(
            self.save_data.stock_ball, 1
        )
