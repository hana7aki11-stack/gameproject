from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    RealTimeSaveData,
    RealTimeClearLog,
    RealTimeActionLog,
    RealTimeSitterLog,
)

from .time_system import (
    apply_elapsed_time,
    change_bedtime,
    start_sitter,
    end_sitter,
)


JST = ZoneInfo("Asia/Tokyo")


class RealTimeSystemTests(TestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="realtime_time_test",
            password="test-password"
        )

    def create_save(self, start, **kwargs):
        values = {
            "user": self.user,
            "status": "playing",
            "has_started_game": True,
            "tutorial_step": 4,
            "play_started_at": start,
            "last_updated_at": start,
        }
        values.update(kwargs)
        return RealTimeSaveData.objects.create(**values)

    def test_one_hour_awake(self):
        """通常時に1時間経過した場合"""
        start = datetime(2026, 11, 17, 12, 0, tzinfo=JST)
        end = datetime(2026, 11, 17, 13, 0, tzinfo=JST)

        save = self.create_save(start)
        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.satisfaction, Decimal("46"))
        self.assertEqual(save.energy, Decimal("48.5"))
        self.assertEqual(save.fullness, Decimal("44"))
        self.assertEqual(save.growth, Decimal("1.2"))

    def test_one_hour_sleep(self):
        """睡眠中に1時間経過した場合"""
        start = datetime(2026, 11, 17, 23, 0, tzinfo=JST)
        end = datetime(2026, 11, 18, 0, 0, tzinfo=JST)

        save = self.create_save(start)
        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.satisfaction, Decimal("50"))
        self.assertEqual(save.energy, Decimal("58"))
        self.assertEqual(save.fullness, Decimal("50"))
        self.assertEqual(save.growth, Decimal("0"))

    def test_low_condition_growth(self):
        """状態が悪い場合、自然成長が遅くなる"""
        start = datetime(2026, 11, 17, 12, 0, tzinfo=JST)
        end = datetime(2026, 11, 17, 13, 0, tzinfo=JST)

        save = self.create_save(
            start,
            satisfaction=Decimal("20")
        )

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.growth, Decimal("0.3"))

    def test_game_over(self):
        """体力が0になった時点でゲームオーバー"""
        start = datetime(2026, 11, 17, 12, 0, tzinfo=JST)
        end = datetime(2026, 11, 17, 14, 0, tzinfo=JST)

        save = self.create_save(
            start,
            energy=Decimal("1.5")
        )

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.status, "game_over")
        self.assertEqual(save.energy, Decimal("0"))
        self.assertEqual(
            save.game_over_at,
            datetime(2026, 11, 17, 13, 0, tzinfo=JST)
        )


    def test_crossing_sleep_hours(self):
        """22時から翌朝8時までの時間経過"""
        start = datetime(2026, 11, 17, 22, 0, tzinfo=JST)
        end = datetime(2026, 11, 18, 8, 0, tzinfo=JST)

        save = self.create_save(start)
        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.satisfaction, Decimal("42"))
        self.assertEqual(save.fullness, Decimal("38"))
        self.assertEqual(save.energy, Decimal("98.5"))
        self.assertEqual(save.growth, Decimal("2.4"))

    def test_natural_growth_clear(self):
        """自然成長で100に達したらクリア"""
        start = datetime(2026, 11, 17, 12, 0, tzinfo=JST)
        end = datetime(2026, 11, 17, 14, 0, tzinfo=JST)

        save = self.create_save(
            start,
            growth=Decimal("99")
        )

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.status, "cleared")
        self.assertEqual(save.growth, Decimal("100"))
        self.assertEqual(save.clear_count, 1)
        self.assertIsNotNone(save.cleared_at)

    def test_no_double_counting(self):
        """同じ時刻で2回更新しても二重計算しない"""
        start = datetime(2026, 11, 17, 12, 0, tzinfo=JST)
        end = datetime(2026, 11, 17, 13, 0, tzinfo=JST)

        save = self.create_save(start)

        apply_elapsed_time(save, now=end)
        apply_elapsed_time(save, now=end)

        save.refresh_from_db()

        self.assertEqual(save.growth, Decimal("1.2"))
        self.assertEqual(
            save.natural_growth_total,
            Decimal("1.2")
        )



    def test_clear_log_created(self):
        """自然成長でクリアした際にクリア記録が保存される"""
        start = datetime(2026, 11, 17, 12, 0, tzinfo=JST)
        end = datetime(2026, 11, 17, 14, 0, tzinfo=JST)

        save = self.create_save(
            start,
            growth=Decimal("99")
        )

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.status, "cleared")

        logs = RealTimeClearLog.objects.filter(
            user=self.user,
            game_round=save.game_round
        )

        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertEqual(log.cleared_at, save.cleared_at)
        self.assertEqual(log.natural_growth_total, Decimal("1.0"))
        self.assertEqual(log.elapsed_seconds, 3000)

        # 同じ時刻で再実行しても記録が増えない
        apply_elapsed_time(save, now=end)

        self.assertEqual(
            RealTimeClearLog.objects.filter(
                user=self.user,
                game_round=save.game_round
            ).count(),
            1
        )


    def test_custom_bedtime_sleep(self):
        """21時に入眠する設定での睡眠"""
        start = datetime(2026, 11, 17, 21, 0, tzinfo=JST)
        end = datetime(2026, 11, 17, 22, 0, tzinfo=JST)

        save = self.create_save(
            start,
            bedtime=time(21, 0)
        )

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.energy, Decimal("58"))
        self.assertEqual(save.satisfaction, Decimal("50"))
        self.assertEqual(save.fullness, Decimal("50"))
        self.assertEqual(save.growth, Decimal("0"))


    def test_custom_bedtime_wakeup(self):
        """21時に入眠し、翌5時に起床する"""
        start = datetime(2026, 11, 17, 21, 0, tzinfo=JST)
        end = datetime(2026, 11, 18, 6, 0, tzinfo=JST)

        save = self.create_save(
            start,
            bedtime=time(21, 0)
        )

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.energy, Decimal("98.5"))
        self.assertEqual(save.satisfaction, Decimal("46"))
        self.assertEqual(save.fullness, Decimal("44"))
        self.assertEqual(save.growth, Decimal("1.2"))


    def test_custom_bedtime_minutes(self):
        """分単位の入眠時刻にも対応する"""
        start = datetime(2026, 11, 17, 22, 0, tzinfo=JST)
        end = datetime(2026, 11, 17, 23, 0, tzinfo=JST)

        save = self.create_save(
            start,
            bedtime=time(22, 30)
        )

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.energy, Decimal("53.25"))
        self.assertEqual(save.satisfaction, Decimal("48"))
        self.assertEqual(save.fullness, Decimal("47"))
        self.assertEqual(save.growth, Decimal("0.6"))


    def test_change_bedtime(self):
        """入眠時刻を変更できるか"""
        start = datetime(
            2026, 11, 17, 22, 0, tzinfo=JST
        )

        save = self.create_save(start)

        change_bedtime(
            save,
            time(21, 0),
            now=start
        )

        save.refresh_from_db()

        self.assertEqual(
            save.bedtime,
            time(21, 0)
        )


    def test_bedtime_change_elapsed_time(self):
        """変更前後の時間が正しく計算されるか"""
        start = datetime(
            2026, 11, 17, 21, 0, tzinfo=JST
        )

        change_at = datetime(
            2026, 11, 17, 22, 0, tzinfo=JST
        )

        end = datetime(
            2026, 11, 17, 23, 0, tzinfo=JST
        )

        save = self.create_save(
            start,
            bedtime=time(23, 0)
        )

        # 22時に入眠時刻を21時へ変更
        change_bedtime(
            save,
            time(21, 0),
            now=change_at
        )

        save.refresh_from_db()

        # 変更前の1時間は活動時間
        self.assertEqual(
            save.energy, Decimal("48.5")
        )

        # 変更後の1時間は睡眠時間
        apply_elapsed_time(save, now=end)

        save.refresh_from_db()

        self.assertEqual(
            save.energy, Decimal("56.5")
        )
        self.assertEqual(
            save.satisfaction, Decimal("46")
        )
        self.assertEqual(
            save.fullness, Decimal("44")
        )
        self.assertEqual(
            save.growth, Decimal("1.2")
        )


    def test_bedtime_change_log(self):
        """入眠時刻の変更ログが保存されるか"""
        start = datetime(
            2026, 11, 17, 12, 0, tzinfo=JST
        )

        save = self.create_save(start)

        change_bedtime(
            save,
            time(22, 30),
            now=start
        )

        logs = RealTimeActionLog.objects.filter(
            user=self.user,
            action="change_bedtime"
        )

        self.assertEqual(logs.count(), 1)

        log = logs.first()

        self.assertEqual(
            log.result,
            "23:00 → 22:30"
        )

        self.assertEqual(
            log.timestamp,
            start
        )



    def test_sitter_start(self):
        """利用可能時間内に預けられる"""
        start = datetime(
            2026, 11, 17, 10, 0, tzinfo=JST
        )

        save = self.create_save(start)

        save, success, message = start_sitter(
            save, now=start
        )

        self.assertTrue(success)
        self.assertEqual(save.sitter_started_at, start)

        self.assertEqual(
            RealTimeSitterLog.objects.filter(
                user=self.user
            ).count(),
            1
        )


    def test_sitter_unavailable_hours(self):
        """朝6時より前と19時以降は利用できない"""
        start = datetime(
            2026, 11, 17, 5, 0, tzinfo=JST
        )

        save = self.create_save(start)

        for hour in [5, 19]:
            now = start.replace(hour=hour)

            save, success, message = start_sitter(
                save, now=now
            )

            self.assertFalse(success)
            self.assertIsNone(save.sitter_started_at)

        self.assertEqual(
            RealTimeSitterLog.objects.filter(
                user=self.user
            ).count(),
            0
        )


    def test_sitter_freezes_parameters(self):
        """シッター利用中はパラメータが変化しない"""
        start = datetime(
            2026, 11, 17, 10, 0, tzinfo=JST
        )
        end = start.replace(hour=13)

        save = self.create_save(start)

        save, success, message = start_sitter(
            save, now=start
        )
        self.assertTrue(success)

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.energy, Decimal("50"))
        self.assertEqual(save.satisfaction, Decimal("50"))
        self.assertEqual(save.fullness, Decimal("50"))
        self.assertEqual(save.growth, Decimal("0"))


    def test_sitter_during_sleep(self):
        """シッター利用中でも睡眠による体力回復を行う"""
        start = datetime(
            2026, 11, 17, 6, 0, tzinfo=JST
        )
        end = start.replace(hour=10)

        save = self.create_save(
            start,
            bedtime=time(1, 0)
        )

        save, success, message = start_sitter(
            save, now=start
        )
        self.assertTrue(success)

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        # 6時〜9時の3時間は睡眠
        # 9時〜10時はシッターによって変化停止

        self.assertEqual(save.energy, Decimal("74"))
        self.assertEqual(save.satisfaction, Decimal("50"))
        self.assertEqual(save.fullness, Decimal("50"))
        self.assertEqual(save.growth, Decimal("0"))


    def test_sitter_manual_end(self):
        """途中でお迎えすると利用記録が保存される"""
        start = datetime(
            2026, 11, 17, 10, 0, tzinfo=JST
        )
        end = start.replace(hour=13)

        save = self.create_save(start)

        save, success, message = start_sitter(
            save, now=start
        )
        self.assertTrue(success)

        save, success, message = end_sitter(
            save, now=end
        )

        self.assertTrue(success)
        self.assertIsNone(save.sitter_started_at)

        # 3時間 = 10800秒
        self.assertEqual(
            save.sitter_total_seconds, 10800
        )

        log = RealTimeSitterLog.objects.get(
            user=self.user
        )

        self.assertEqual(log.started_at, start)
        self.assertEqual(log.ended_at, end)
        self.assertFalse(log.auto_ended)

        # お迎え後は通常の時間計算に戻る
        apply_elapsed_time(
            save, now=end.replace(hour=14)
        )
        save.refresh_from_db()

        self.assertEqual(save.energy, Decimal("48.5"))
        self.assertEqual(save.growth, Decimal("1.2"))


    def test_sitter_once_per_day(self):
        """同じ日は再利用できず、翌日は利用できる"""
        start = datetime(
            2026, 11, 17, 10, 0, tzinfo=JST
        )

        save = self.create_save(start)

        save, success, message = start_sitter(
            save, now=start
        )
        self.assertTrue(success)

        save, success, message = end_sitter(
            save, now=start.replace(hour=18)
        )
        self.assertTrue(success)

        # 同じ日の再利用
        save, success, message = start_sitter(
            save,
            now=start.replace(hour=18, minute=30)
        )
        self.assertFalse(success)

        # 翌日の利用
        next_day = datetime(
            2026, 11, 18, 6, 0, tzinfo=JST
        )

        save, success, message = start_sitter(
            save, now=next_day
        )

        self.assertTrue(success)


    def test_sitter_auto_end(self):
        """19時に自動でお迎えされる"""
        start = datetime(
            2026, 11, 17, 18, 0, tzinfo=JST
        )
        end = start.replace(hour=20)

        save = self.create_save(start)

        save, success, message = start_sitter(
            save, now=start
        )
        self.assertTrue(success)

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertIsNone(save.sitter_started_at)
        self.assertEqual(save.sitter_total_seconds, 3600)

        # 19時〜20時は通常の育成時間
        self.assertEqual(save.energy, Decimal("48.5"))
        self.assertEqual(save.satisfaction, Decimal("46"))
        self.assertEqual(save.fullness, Decimal("44"))
        self.assertEqual(save.growth, Decimal("1.2"))

        log = RealTimeSitterLog.objects.get(
            user=self.user
        )

        self.assertEqual(
            log.ended_at,
            start.replace(hour=19)
        )
        self.assertTrue(log.auto_ended)


    def test_sitter_offline_until_next_day(self):
        """翌朝までゲームを開かなくても19時に利用終了"""
        start = datetime(
            2026, 11, 17, 18, 0, tzinfo=JST
        )
        end = datetime(
            2026, 11, 18, 8, 0, tzinfo=JST
        )

        save = self.create_save(start)

        save, success, message = start_sitter(
            save, now=start
        )
        self.assertTrue(success)

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertIsNone(save.sitter_started_at)
        self.assertEqual(save.sitter_total_seconds, 3600)

        log = RealTimeSitterLog.objects.get(
            user=self.user
        )

        self.assertEqual(
            log.ended_at,
            start.replace(hour=19)
        )
        self.assertTrue(log.auto_ended)

        # 再計算しても利用時間が二重加算されない
        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(save.sitter_total_seconds, 3600)
        self.assertEqual(
            RealTimeSitterLog.objects.filter(
                user=self.user
            ).count(),
            1
        )


    # =========================
    # チュートリアル中の時間停止
    # =========================

    def test_tutorial_freezes_parameters(self):
        """イントロ・チュートリアル中は自然変動しない"""

        start = datetime(
            2026, 11, 17, 12, 0, tzinfo=JST
        )
        end = start + timedelta(hours=3)

        save = self.create_save(
            start,
            tutorial_step=0
        )

        for step in range(4):

            with self.subTest(step=step):

                save.tutorial_step = step
                save.last_updated_at = start

                save.save(
                    update_fields=[
                        "tutorial_step",
                        "last_updated_at",
                    ]
                )

                apply_elapsed_time(save, now=end)
                save.refresh_from_db()

                self.assertEqual(
                    save.satisfaction, Decimal("50")
                )
                self.assertEqual(
                    save.energy, Decimal("50")
                )
                self.assertEqual(
                    save.fullness, Decimal("50")
                )
                self.assertEqual(
                    save.growth, Decimal("0")
                )
                self.assertEqual(
                    save.natural_growth_total,
                    Decimal("0")
                )
                self.assertEqual(
                    save.last_updated_at, end
                )
                self.assertEqual(
                    save.status, "playing"
                )

        # 時間経過ログも作成されない
        self.assertFalse(
            RealTimeActionLog.objects.filter(
                user=self.user,
                action="time_update"
            ).exists()
        )


    def test_tutorial_freezes_sleep_recovery(self):
        """チュートリアル中は睡眠による回復も発生しない"""

        start = datetime(
            2026, 11, 17, 23, 0, tzinfo=JST
        )
        end = start + timedelta(hours=2)

        save = self.create_save(
            start,
            tutorial_step=1
        )

        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(
            save.energy, Decimal("50")
        )
        self.assertEqual(
            save.growth, Decimal("0")
        )
        self.assertEqual(
            save.last_updated_at, end
        )


    def test_time_resumes_after_tutorial(self):
        """チュートリアル終了後は通常の時間経過に戻る"""

        start = datetime(
            2026, 11, 17, 12, 0, tzinfo=JST
        )

        tutorial_end = start + timedelta(hours=2)
        end = tutorial_end + timedelta(hours=1)

        save = self.create_save(
            start,
            tutorial_step=3
        )

        # チュートリアル中の2時間
        apply_elapsed_time(
            save, now=tutorial_end
        )

        save.refresh_from_db()

        # チュートリアルを終了した状態に変更
        save.tutorial_step = 4

        save.save(
            update_fields=["tutorial_step"]
        )

        # 通常の育成を1時間進める
        apply_elapsed_time(save, now=end)
        save.refresh_from_db()

        self.assertEqual(
            save.satisfaction, Decimal("46")
        )
        self.assertEqual(
            save.energy, Decimal("48.5")
        )
        self.assertEqual(
            save.fullness, Decimal("44")
        )
        self.assertEqual(
            save.growth, Decimal("1.2")
        )
