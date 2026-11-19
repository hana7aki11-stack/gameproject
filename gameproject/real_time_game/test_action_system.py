from decimal import Decimal
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from .action_system import (
    get_basic_reward,
    draw_item,
    ALL_ITEMS,
    apply_parameter_events,
)

class ActionSystemTests(TestCase):

    # =========================
    # 好きなごはん選び
    # =========================

    def test_food(self):

        r = get_basic_reward(
            'food',
            lives=3
        )

        self.assertEqual(
            (
                r.satisfaction,
                r.energy,
                r.fullness,
                r.growth,
            ),
            (20, 5, 30, Decimal('2.4'))
        )


    # =========================
    # 火加減チャレンジ
    # =========================

    def test_timing(self):

        r = get_basic_reward(
            'timing',
            lives=3
        )

        self.assertEqual(
            r.growth,
            Decimal('3.6')
        )


    # =========================
    # 食材かぞえ
    # =========================

    def test_count(self):

        r = get_basic_reward(
            'count',
            lives=0
        )

        self.assertEqual(r.growth, 0)


    # =========================
    # 障害物よけ
    # =========================

    def test_dodge_bonus(self):

        r = get_basic_reward(
            'dodge',
            lives=3,
            score=5
        )

        self.assertEqual(
            (r.satisfaction, r.growth),
            (17, Decimal('4.8'))
        )


    # =========================
    # ボールキャッチ
    # =========================

    def test_ball(self):

        for score, growth in [
            (0, '1.2'),
            (10, '2.4'),
            (15, '3.6'),
        ]:

            r = get_basic_reward(
                'ball',
                score=score
            )

            self.assertEqual(
                (r.energy, r.fullness, r.growth),
                (-10, -10, Decimal(growth))
            )

            self.assertEqual(
                r.success,
                score >= 10
            )


    # =========================
    # ダンスまね
    # =========================

    def test_dance(self):

        r = get_basic_reward(
            'dance',
            result='clear',
            difficulty='oni'
        )

        self.assertEqual(
            r.growth,
            Decimal('4.8')
        )

        r = get_basic_reward(
            'dance',
            result='fail'
        )

        self.assertEqual(
            (r.satisfaction, r.growth, r.success),
            (4, 0, False)
        )


    # =========================
    # 休む
    # =========================

    def test_rest(self):

        for energy, sat, gain in [
            (40, 8, 35),
            (41, 0, 25),
        ]:

            r = get_basic_reward(
                'rest',
                energy=energy
            )

            self.assertEqual(
                (r.satisfaction, r.energy, r.fullness),
                (sat, gain, -3)
            )


    # =========================
    # 不正な入力値
    # =========================

    def test_invalid_input(self):

        with self.assertRaises(ValueError):

            get_basic_reward(
                'food',
                lives=4
            )


    # =========================
    # 家具を獲得できない条件
    # =========================

    def test_no_item_when_not_happy_or_all_owned(self):

        self.assertIsNone(
            draw_item([], 'normal')
        )

        self.assertIsNone(
            draw_item(ALL_ITEMS, 'happy')
        )


    # =========================
    # 家具抽選にはずれた場合
    # =========================

    @patch('random.randint', return_value=31)
    def test_no_drop(self, roll):

        self.assertIsNone(
            draw_item([], 'happy')
        )


    # =========================
    # 未獲得家具だけを抽選する
    # =========================

    @patch('random.randint', return_value=30)
    def test_only_unowned_item(self, roll):

        owned = list(ALL_ITEMS[:-1])

        self.assertEqual(
            draw_item(owned, 'happy'),
            ALL_ITEMS[-1]
        )

        self.assertEqual(
            owned,
            ALL_ITEMS[:-1]
        )


    # =========================
    # チュートリアル中の成長ボーナス
    # =========================

    def test_tutorial_good_bonus(self):

        now = datetime(
            2026, 11, 17, 12, 0,
            tzinfo=ZoneInfo("Asia/Tokyo")
        )

        for energy, expected_bonus in [
            (70, Decimal("1")),
            (80, Decimal("3")),
        ]:

            with self.subTest(energy=energy):

                save = SimpleNamespace(
                    satisfaction=Decimal("80"),
                    energy=Decimal(energy),
                    fullness=Decimal("50"),
                    growth=Decimal("10"),
                    character_state="normal",
                    last_good_bonus_at=None,
                )

                messages, bonus = apply_parameter_events(
                    save,
                    "food",
                    now,
                    in_tutorial=True
                )

                self.assertEqual(bonus, expected_bonus)
                self.assertEqual(
                    save.growth,
                    Decimal("10") + expected_bonus
                )
                self.assertEqual(
                    save.character_state, "happy"
                )

                # 通常育成のボーナス制限に影響しない
                self.assertIsNone(save.last_good_bonus_at)


    # =========================
    # 練習中はボーナスの時間制限なし
    # =========================

    def test_tutorial_bonus_no_interval(self):

        now = datetime(
            2026, 11, 17, 12, 0,
            tzinfo=ZoneInfo("Asia/Tokyo")
        )

        save = SimpleNamespace(
            satisfaction=Decimal("85"),
            energy=Decimal("85"),
            fullness=Decimal("50"),
            growth=Decimal("0"),
            character_state="normal",
            last_good_bonus_at=None,
        )

        for _ in range(2):

            messages, bonus = apply_parameter_events(
                save,
                "food",
                now,
                in_tutorial=True
            )

            self.assertEqual(bonus, Decimal("3"))

        self.assertEqual(save.growth, Decimal("6"))
        self.assertIsNone(save.last_good_bonus_at)


    # =========================
    # 通常育成中の3時間制限
    # =========================

    def test_normal_bonus_interval(self):

        now = datetime(
            2026, 11, 17, 12, 0,
            tzinfo=ZoneInfo("Asia/Tokyo")
        )

        save = SimpleNamespace(
            satisfaction=Decimal("85"),
            energy=Decimal("85"),
            fullness=Decimal("50"),
            growth=Decimal("0"),
            character_state="normal",
            last_good_bonus_at=None,
        )

        for elapsed, expected_bonus in [
            (0, Decimal("2")),
            (1, Decimal("0")),
            (3, Decimal("2")),
        ]:

            messages, bonus = apply_parameter_events(
                save,
                "food",
                now + timedelta(hours=elapsed)
            )

            self.assertEqual(bonus, expected_bonus)

        self.assertEqual(save.growth, Decimal("4"))


    # =========================
    # 練習中も状態依存イベントが発生
    # =========================

    def test_tutorial_parameter_penalty(self):

        now = datetime(
            2026, 11, 17, 12, 0,
            tzinfo=ZoneInfo("Asia/Tokyo")
        )

        save = SimpleNamespace(
            satisfaction=Decimal("50"),
            energy=Decimal("95"),
            fullness=Decimal("50"),
            growth=Decimal("10"),
            character_state="normal",
            last_good_bonus_at=None,
        )

        messages, bonus = apply_parameter_events(
            save,
            "rest",
            now,
            in_tutorial=True
        )

        # 元気なのに休んだ場合のペナルティ
        self.assertEqual(save.satisfaction, 35)
        self.assertEqual(save.growth, 8)
        self.assertEqual(save.character_state, "tired")
        self.assertEqual(bonus, 0)