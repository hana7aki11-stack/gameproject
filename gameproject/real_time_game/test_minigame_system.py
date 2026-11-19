from unittest.mock import patch
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    RealTimeSaveData,
    RealTimeMinigameSession,
    RealTimeActionLog,
)

from .minigame_system import (
    start_minigame,
    finish_minigame,
    abandon_minigame,
)

from .action_system import apply_action


JST = ZoneInfo("Asia/Tokyo")


class MinigameSystemTests(TestCase):

    def setUp(self):

        self.user = (
            get_user_model().objects.create_user(
                username="minigame_test"
            )
        )

        self.now = datetime(
            2026, 11, 17,
            10, 0,
            tzinfo=JST
        )

        self.save_data = (
            RealTimeSaveData.objects.create(
                user=self.user,
                status="playing",
                has_started_game=True,
                tutorial_step=4,
                play_started_at=self.now,
                last_updated_at=self.now,
            )
        )

    # =========================
    # 開始時にストック消費
    # =========================

    def test_start(self):

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=self.now
        )

        self.assertTrue(success)
        self.assertEqual(save.stock_ball, 1)
        self.assertEqual(save.growth, 0)

        session = RealTimeMinigameSession.objects.get(
            user=self.user
        )

        self.assertEqual(
            session.status, "playing"
        )

        self.assertEqual(
            str(session.token),
            info["token"]
        )

        self.assertTrue(
            session.stock_consumed
        )

    # =========================
    # 終了時に報酬を反映
    # =========================

    def test_finish(self):

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=self.now
        )

        token = info["token"]

        save, success, info = finish_minigame(
            save,
            token,
            score=10,
            now=self.now
        )

        self.assertTrue(success)

        self.assertEqual(
            save.growth,
            Decimal("2.4")
        )

        # 二重に消費されていない
        self.assertEqual(save.stock_ball, 1)

        session = RealTimeMinigameSession.objects.get(
            token=token
        )

        self.assertEqual(
            session.status, "completed"
        )

        self.assertTrue(session.success)

    # =========================
    # 二重報酬の防止
    # =========================

    def test_duplicate_finish(self):

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=self.now
        )

        token = info["token"]

        save, success, info = finish_minigame(
            save, token,
            score=10,
            now=self.now
        )

        growth = save.growth

        save, success, info = finish_minigame(
            save, token,
            score=10,
            now=self.now
        )

        self.assertFalse(success)
        self.assertEqual(save.growth, growth)

        self.assertEqual(
            save.minigame_ball_play, 1
        )

    # =========================
    # 同時に複数のゲームを開始できない
    # =========================

    def test_duplicate_start(self):

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=self.now
        )

        save, success, info = start_minigame(
            save,
            "food",
            now=self.now
        )

        self.assertFalse(success)
        self.assertEqual(save.stock_food, 2)

    # =========================
    # ストック不足
    # =========================

    def test_empty_stock(self):

        self.save_data.stock_ball = 0
        self.save_data.save()

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=self.now
        )

        self.assertFalse(success)

        self.assertEqual(
            RealTimeMinigameSession.objects.count(),
            0
        )

    # =========================
    # 途中離脱
    # =========================

    def test_abandon(self):

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=self.now
        )

        token = info["token"]

        save, success, info = abandon_minigame(
            save,
            token,
            now=self.now
        )

        self.assertTrue(success)
        self.assertEqual(save.stock_ball, 1)
        self.assertEqual(save.growth, 0)

        session = RealTimeMinigameSession.objects.get(
            token=token
        )

        self.assertEqual(
            session.status, "abandoned"
        )

    # =========================
    # 制限時間超過
    # =========================

    def test_timeout(self):

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=self.now
        )

        token = info["token"]

        save, success, info = finish_minigame(
            save,
            token,
            score=15,
            now=self.now + timedelta(minutes=16)
        )

        self.assertFalse(success)

        self.assertEqual(
            save.active_growth_total, 0
        )

        session = RealTimeMinigameSession.objects.get(
            token=token
        )

        self.assertEqual(
            session.status, "abandoned"
        )

    # =========================
    # プレイ時間の記録
    # =========================

    def test_duration(self):

        save, success, info = start_minigame(
            self.save_data,
            "food",
            now=self.now
        )

        token = info["token"]

        save, success, info = finish_minigame(
            save,
            token,
            lives=3,
            now=self.now + timedelta(seconds=45)
        )

        self.assertTrue(success)

        session = RealTimeMinigameSession.objects.get(
            token=token
        )

        self.assertEqual(
            session.duration_seconds(), 45
        )

    # =========================
    # ミニゲーム中も自然成長
    # =========================

    def test_natural_growth(self):

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=self.now
        )

        token = info["token"]

        save, success, info = finish_minigame(
            save,
            token,
            score=10,
            now=self.now + timedelta(minutes=5)
        )

        self.assertTrue(success)

        self.assertEqual(
            save.natural_growth_total,
            Decimal("0.1")
        )

        self.assertEqual(
            save.active_growth_total,
            Decimal("2.4")
        )

    # =========================
    # 未解放の難易度
    # =========================

    def test_locked_difficulty(self):

        save, success, info = start_minigame(
            self.save_data,
            "dance",
            difficulty="oni",
            now=self.now
        )

        self.assertFalse(success)
        self.assertEqual(save.stock_dance, 2)

    # =========================
    # チュートリアル
    # =========================

    def test_tutorial(self):
        self.save_data.tutorial_step = 1
        self.save_data.fullness = 25
        self.save_data.save()

        # STEP1：好きなごはん選び
        save, success, info = start_minigame(
            self.save_data,
            "food",
            difficulty="oni",
            now=self.now
        )

        self.assertTrue(success, info["message"])

        token = info["token"]

        # 難易度は「かんたん」に固定
        self.assertEqual(info["difficulty"], "easy")

        # ストックは消費されない
        self.assertEqual(save.stock_food, 2)

        session = RealTimeMinigameSession.objects.get(
            token=token
        )

        # チュートリアルとして記録
        self.assertTrue(session.is_tutorial)
        self.assertFalse(session.stock_consumed)

        # ミニゲーム終了
        save, success, info = finish_minigame(
            save,
            token,
            lives=3,
            now=self.now + timedelta(seconds=45)
        )

        self.assertTrue(success, info["message"])
        save.refresh_from_db()

        # ストックは消費されていない
        self.assertEqual(save.stock_food, 2)

        # STEP2へ進む
        self.assertEqual(save.tutorial_step, 2)

        # 満腹度が増加している
        self.assertGreater(save.fullness, 25)

        # 自然成長は発生しない
        self.assertEqual(save.natural_growth_total, 0)

        # チュートリアル中も行動回数に加算する
        self.assertEqual(save.action_food_count, 1)
        self.assertEqual(save.minigame_food_play, 1)
        self.assertEqual(save.minigame_food_success, 1)
        self.assertEqual(save.healthy_food_count, 1)

    # =========================
    # 他人の識別IDは使用できない
    # =========================

    def test_other_user_token(self):

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=self.now
        )

        token = info["token"]

        other_user = (
            get_user_model().objects.create_user(
                username="other_user"
            )
        )

        other_save = (
            RealTimeSaveData.objects.create(
                user=other_user,
                status="playing",
                tutorial_step=4,
                last_updated_at=self.now,
                play_started_at=self.now,
            )
        )

        other_save, success, info = finish_minigame(
            other_save,
            token,
            score=15,
            now=self.now
        )

        self.assertFalse(success)
        self.assertEqual(other_save.growth, 0)

    # =========================
    # 睡眠中は開始できない
    # =========================

    def test_sleep(self):

        now = self.now.replace(hour=23)

        self.save_data.last_updated_at = now
        self.save_data.save()

        save, success, info = start_minigame(
            self.save_data,
            "ball",
            now=now
        )

        self.assertFalse(success)
        self.assertEqual(save.stock_ball, 2)


    # =========================
    # チュートリアル中の行動制限
    # =========================

    def test_tutorial_action_restriction(self):

        # 各STEPで禁止されているミニゲーム
        cases = [
            (0, "food"),
            (1, "ball"),
            (1, "dance"),
            (2, "food"),
            (3, "dance"),
            (5, "ball"),
            (5, "food"),
            (5, "timing"),
            (5, "count"),
            (5, "dodge"),
            (5, "dance"),
        ]

        for step, action in cases:

            with self.subTest(step=step, action=action):

                self.save_data.refresh_from_db()
                self.save_data.tutorial_step = step
                self.save_data.save()

                save, success, info = start_minigame(
                    self.save_data,
                    action,
                    now=self.now
                )

                self.assertFalse(success)

        # ミニゲームは開始されていない
        self.assertEqual(
            RealTimeMinigameSession.objects.count(),
            0
        )


    # =========================
    # 睡眠時間帯でも練習できる
    # =========================

    def test_tutorial_during_sleep(self):

        now = self.now.replace(hour=23)

        self.save_data.tutorial_step = 1
        self.save_data.last_updated_at = now
        self.save_data.save()

        save, success, info = start_minigame(
            self.save_data,
            "food",
            now=now
        )

        self.assertTrue(success, info["message"])

        token = info["token"]

        save, success, info = finish_minigame(
            save,
            token,
            lives=3,
            now=now + timedelta(seconds=45)
        )

        self.assertTrue(success, info["message"])
        self.assertEqual(save.tutorial_step, 2)
        self.assertEqual(save.stock_food, 2)


    # =========================
    # チュートリアル中の途中離脱
    # =========================

    def test_tutorial_abandon(self):

        self.save_data.tutorial_step = 1
        self.save_data.save()

        save, success, info = start_minigame(
            self.save_data,
            "food",
            now=self.now
        )

        self.assertTrue(success, info["message"])

        token = info["token"]

        save, success, info = abandon_minigame(
            save,
            token,
            now=self.now + timedelta(seconds=10)
        )

        self.assertTrue(success, info["message"])

        save.refresh_from_db()

        # 途中離脱ではSTEPが進まない
        self.assertEqual(save.tutorial_step, 1)

        # ストックも消費されない
        self.assertEqual(save.stock_food, 2)

        session = RealTimeMinigameSession.objects.get(
            token=token
        )

        self.assertEqual(session.status, "abandoned")


    # =========================
    # 失敗しても最後まで遊べば進行
    # =========================

    def test_tutorial_failed_minigame(self):

        self.save_data.tutorial_step = 2
        self.save_data.save()

        save, success, info = start_minigame(
            self.save_data,
            "dance",
            now=self.now
        )

        self.assertTrue(success, info["message"])

        token = info["token"]

        save, success, info = finish_minigame(
            save,
            token,
            result="fail",
            now=self.now + timedelta(seconds=30)
        )

        self.assertTrue(success, info["message"])
        # 失敗しても行動回数には加算する
        self.assertEqual(save.action_dance_count, 1)
        self.assertEqual(save.minigame_dance_play, 1)
        self.assertEqual(save.minigame_dance_success, 0)
        self.assertEqual(save.play_count, 1)

        session = RealTimeMinigameSession.objects.get(
            token=token
        )

        self.assertFalse(session.success)
        self.assertEqual(session.status, "completed")


    # =========================
    # チュートリアル終了
    # =========================

    def test_tutorial_rest_finish(self):

        self.save_data.tutorial_step = 3
        self.save_data.energy = Decimal("40")
        self.save_data.save()

        now = self.now + timedelta(hours=2)

        save, success, info = apply_action(
            self.save_data,
            "rest",
            now=now
        )

        self.assertTrue(success, info["message"])

        save.refresh_from_db()

        # リアルタイム型の追加説明へ進む
        self.assertEqual(save.tutorial_step, 5)

        # ストック消費なし
        self.assertEqual(save.stock_rest, 2)

        # 体力が回復する
        self.assertGreater(save.energy, 40)

        # チュートリアル中も行動回数に加算する
        self.assertEqual(save.action_rest_count, 1)

        # 通常育成の時間計算の基準
        self.assertEqual(save.last_updated_at, now)

        # 練習中の自然成長はなし
        self.assertEqual(save.natural_growth_total, 0)

    # =========================
    # 追加説明中は休むこともできない
    # =========================

    def test_extra_intro_rest_restriction(self):

        self.save_data.tutorial_step = 5
        self.save_data.energy = Decimal("40")
        self.save_data.save()

        save, success, info = apply_action(
            self.save_data,
            "rest",
            now=self.now
        )

        self.assertFalse(success)

        save.refresh_from_db()

        self.assertEqual(save.energy, 40)
        self.assertEqual(save.stock_rest, 2)
        self.assertEqual(save.tutorial_step, 5)
        self.assertEqual(save.action_rest_count, 0)

    # =========================
    # チュートリアル中の家具獲得
    # =========================

    @patch("random.randint", return_value=1)
    def test_tutorial_item_drop(self, roll):

        self.save_data.tutorial_step = 1
        self.save_data.satisfaction = Decimal("70")
        self.save_data.energy = Decimal("50")
        self.save_data.fullness = Decimal("25")
        self.save_data.save()

        save, success, info = start_minigame(
            self.save_data,
            "food",
            now=self.now
        )

        self.assertTrue(success, info["message"])

        token = info["token"]

        save, success, info = finish_minigame(
            save,
            token,
            lives=3,
            now=self.now + timedelta(seconds=45)
        )

        self.assertTrue(success, info["message"])

        save.refresh_from_db()

        # 家具を1個獲得
        self.assertEqual(len(save.items), 1)

        # NEWアイテムとして記録
        self.assertEqual(save.new_items, save.items)

        # チュートリアル中はストック消費なし
        self.assertEqual(save.stock_food, 2)

        # 自然成長なし
        self.assertEqual(save.natural_growth_total, 0)

        # 成長度：基本報酬2.4＋ボーナス1
        self.assertEqual(
            save.growth,
            Decimal("3.4")
        )

        # 研究用ログでは練習と区別できる
        self.assertTrue(
            RealTimeActionLog.objects.filter(
                user=self.user,
                game_round=save.game_round,
                action="好きなごはん選び",
                result__contains="[練習]",
            ).exists()
        )