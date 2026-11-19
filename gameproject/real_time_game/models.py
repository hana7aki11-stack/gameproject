import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import time


class RealTimeSaveData(models.Model):
    """リアルタイム型のアカウント別育成データ。"""

    STATUS_CHOICES = [
        ('not_started', '未開始'),
        ('playing', '育成中'),
        ('cleared', 'クリア'),
        ('game_over', 'ゲームオーバー'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='ユーザー')
    has_started_game = models.BooleanField(default=False, verbose_name='ニューゲーム開始済み')
    game_round = models.PositiveIntegerField(default=1, verbose_name='育成回数')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started', verbose_name='育成状態')

    satisfaction = models.DecimalField(max_digits=8, decimal_places=4, default=50, verbose_name='満足度')
    energy = models.DecimalField(max_digits=8, decimal_places=4, default=50, verbose_name='体力')
    fullness = models.DecimalField(max_digits=8, decimal_places=4, default=50, verbose_name='満腹度')
    growth = models.DecimalField(max_digits=8, decimal_places=4, default=0, verbose_name='成長度')

    play_started_at = models.DateTimeField(null=True, blank=True, verbose_name='育成開始日時')
    last_updated_at = models.DateTimeField(default=timezone.now, verbose_name='最終状態更新日時')
    cleared_at = models.DateTimeField(null=True, blank=True, verbose_name='クリア日時')
    game_over_at = models.DateTimeField(null=True, blank=True, verbose_name='ゲームオーバー日時')
    last_good_bonus_at = models.DateTimeField(null=True, blank=True, verbose_name='良い状態ボーナス最終獲得日時')

    # =========================
    # 睡眠時間の設定
    # =========================

    bedtime = models.TimeField(
        default=time(23, 0),
        verbose_name='入眠時刻'
    )

    sitter_started_at = models.DateTimeField(null=True, blank=True, verbose_name='現在のシッター開始日時')
    sitter_last_used_date = models.DateField(null=True, blank=True, verbose_name='シッター最終利用日（日本時間）')
    sitter_total_seconds = models.PositiveIntegerField(default=0, verbose_name='今の育成のシッター累計秒数')

    # ストックと回復時刻はミニゲームごとに独立させる。
    stock_ball = models.PositiveSmallIntegerField(default=2, verbose_name='ボールキャッチ残数')
    stock_food = models.PositiveSmallIntegerField(default=2, verbose_name='ごはん選び残数')
    stock_dodge = models.PositiveSmallIntegerField(default=2, verbose_name='障害物よけ残数')
    stock_dance = models.PositiveSmallIntegerField(default=2, verbose_name='ダンスまね残数')
    stock_timing = models.PositiveSmallIntegerField(default=2, verbose_name='火加減チャレンジ残数')
    stock_count = models.PositiveSmallIntegerField(default=2, verbose_name='食材かぞえ残数')
    stock_rest = models.PositiveSmallIntegerField(default=2, verbose_name='休む残数')
    stock_recovery_at = models.JSONField(default=dict, verbose_name='各ストックの次回回復日時')

    play_count = models.PositiveIntegerField(default=0, verbose_name='プレイ回数')
    healthy_food_count = models.PositiveIntegerField(default=0, verbose_name='健康的な食事回数')
    snack_count = models.PositiveIntegerField(default=0, verbose_name='おやつ回数')
    play_session_count = models.PositiveIntegerField(default=0, verbose_name='プレイセッション数')
    round_play_seconds = models.PositiveIntegerField(default=0, verbose_name='今の育成のプレイ時間（秒）')
    clear_count = models.PositiveIntegerField(default=0, verbose_name='育成クリア回数')
    game_over_count = models.PositiveIntegerField(default=0, verbose_name='ゲームオーバー回数')
    clear_time_seconds = models.PositiveIntegerField(default=0, verbose_name='クリアまでの経過秒数')

    # ターン制と共通する行動別・成功別カウンター。
    action_rest_count = models.PositiveIntegerField(default=0, verbose_name='休む選択回数')
    action_ball_count = models.PositiveIntegerField(default=0, verbose_name='ボールキャッチ選択回数')
    action_food_count = models.PositiveIntegerField(default=0, verbose_name='ごはん選び選択回数')
    action_dodge_count = models.PositiveIntegerField(default=0, verbose_name='障害物よけ選択回数')
    action_dance_count = models.PositiveIntegerField(default=0, verbose_name='ダンスまね選択回数')
    action_timing_count = models.PositiveIntegerField(default=0, verbose_name='火加減チャレンジ選択回数')
    action_count_count = models.PositiveIntegerField(default=0, verbose_name='食材かぞえ選択回数')
    minigame_ball_play = models.PositiveIntegerField(default=0, verbose_name='ボールキャッチプレイ回数')
    minigame_ball_success = models.PositiveIntegerField(default=0, verbose_name='ボールキャッチ成功回数')
    minigame_food_play = models.PositiveIntegerField(default=0, verbose_name='ごはん選びプレイ回数')
    minigame_food_success = models.PositiveIntegerField(default=0, verbose_name='ごはん選び成功回数')
    minigame_dodge_play = models.PositiveIntegerField(default=0, verbose_name='障害物よけプレイ回数')
    minigame_dodge_success = models.PositiveIntegerField(default=0, verbose_name='障害物よけ成功回数')
    minigame_dance_play = models.PositiveIntegerField(default=0, verbose_name='ダンスまねプレイ回数')
    minigame_dance_success = models.PositiveIntegerField(default=0, verbose_name='ダンスまね成功回数')
    minigame_timing_play = models.PositiveIntegerField(default=0, verbose_name='火加減チャレンジプレイ回数')
    minigame_timing_success = models.PositiveIntegerField(default=0, verbose_name='火加減チャレンジ成功回数')
    minigame_count_play = models.PositiveIntegerField(default=0, verbose_name='食材かぞえプレイ回数')
    minigame_count_success = models.PositiveIntegerField(default=0, verbose_name='食材かぞえ成功回数')

    natural_growth_total = models.DecimalField(max_digits=10, decimal_places=4, default=0, verbose_name='今の育成の自然成長累計')
    active_growth_total = models.DecimalField(max_digits=10, decimal_places=4, default=0, verbose_name='今の育成のお世話による成長累計')
    character_state = models.CharField(max_length=20, default='normal', verbose_name='キャラクター状態')
    room_wallpaper = models.CharField(max_length=50, default='room-default', verbose_name='部屋の壁紙')
    items = models.JSONField(default=list, verbose_name='所持アイテム')
    placed_items = models.JSONField(default=list, verbose_name='配置アイテム')
    new_items = models.JSONField(default=list, verbose_name='未確認アイテム')
    tutorial_step = models.PositiveSmallIntegerField(default=0, verbose_name='チュートリアル進行')
    notified_stage = models.PositiveSmallIntegerField(default=0, verbose_name='通知済み成長段階')

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = '育成データ'
        verbose_name_plural = '育成データ'


class RealTimeActionLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='ユーザー')
    game_round = models.PositiveIntegerField(default=1, verbose_name='育成回数')
    action = models.CharField(max_length=50, verbose_name='行動')
    timestamp = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='行動日時')
    energy = models.DecimalField(max_digits=8, decimal_places=4, default=50, verbose_name='体力')
    fullness = models.DecimalField(max_digits=8, decimal_places=4, default=50, verbose_name='満腹度')
    satisfaction = models.DecimalField(max_digits=8, decimal_places=4, default=50, verbose_name='満足度')
    growth = models.DecimalField(max_digits=8, decimal_places=4, default=0, verbose_name='成長度')
    result = models.CharField(max_length=100, blank=True, default='', verbose_name='結果')
    growth_delta = models.DecimalField(max_digits=8, decimal_places=4, default=0, verbose_name='今回の成長量')
    natural_growth_delta = models.DecimalField(max_digits=8, decimal_places=4, default=0, verbose_name='今回の自然成長量')
    elapsed_seconds = models.PositiveIntegerField(default=0, verbose_name='今回反映した経過秒数')

    def __str__(self):
        return f'{self.user.username} - {self.action} - {self.timestamp}'

    class Meta:
        verbose_name = '行動ログ'
        verbose_name_plural = '行動ログ'
        ordering = ['-timestamp']


class RealTimePlaySession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='プレイヤー')
    game_round = models.PositiveIntegerField(default=1, verbose_name='育成回数')
    started_at = models.DateTimeField(verbose_name='プレイ開始')
    last_seen_at = models.DateTimeField(verbose_name='プレイ終了（最終操作）')
    logged_out_at = models.DateTimeField(null=True, blank=True, verbose_name='ログアウト時刻')
    page_views = models.PositiveIntegerField(default=0, verbose_name='画面操作回数')

    def duration_seconds(self):
        end = self.logged_out_at or self.last_seen_at
        return max(0, int((end - self.started_at).total_seconds()))

    def __str__(self):
        return f'{self.user.username} {self.started_at:%Y-%m-%d %H:%M}'

    class Meta:
        verbose_name = 'プレイログ'
        verbose_name_plural = 'プレイログ'
        ordering = ['-started_at']


class RealTimeClearLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='プレイヤー')
    game_round = models.PositiveIntegerField(default=1, verbose_name='育成回数')
    clear_number = models.PositiveIntegerField(default=1, verbose_name='クリア回数')
    cleared_at = models.DateTimeField(verbose_name='クリア日時')
    play_seconds = models.PositiveIntegerField(default=0, verbose_name='プレイ時間（秒）')
    elapsed_seconds = models.PositiveIntegerField(default=0, verbose_name='育成開始からの経過時間（秒）')
    natural_growth_total = models.DecimalField(max_digits=10, decimal_places=4, default=0, verbose_name='自然成長累計')
    active_growth_total = models.DecimalField(max_digits=10, decimal_places=4, default=0, verbose_name='お世話による成長累計')
    sitter_seconds = models.PositiveIntegerField(default=0, verbose_name='シッター利用累計秒数')

    def __str__(self):
        return f'{self.user.username} {self.clear_number}回目'

    class Meta:
        verbose_name = 'クリア記録'
        verbose_name_plural = 'クリア記録'
        ordering = ['-cleared_at']


class RealTimeSitterLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='プレイヤー')
    game_round = models.PositiveIntegerField(default=1, verbose_name='育成回数')
    started_at = models.DateTimeField(verbose_name='預け入れ日時')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='お迎え日時')
    auto_ended = models.BooleanField(default=False, verbose_name='19時自動お迎え')

    def duration_seconds(self):
        if self.ended_at is None:
            return None
        return max(0, int((self.ended_at - self.started_at).total_seconds()))

    def __str__(self):
        return f'{self.user.username} {self.started_at:%Y-%m-%d %H:%M}'

    class Meta:
        verbose_name = 'シッター利用記録'
        verbose_name_plural = 'シッター利用記録'
        ordering = ['-started_at']


 # =========================
# ミニゲームのプレイ記録
# =========================

class RealTimeMinigameSession(models.Model):

        ACTION_CHOICES = [
            ("ball", "ボールキャッチ"),
            ("food", "好きなごはん選び"),
            ("timing", "火加減チャレンジ"),
            ("count", "食材かぞえ"),
            ("dodge", "障害物よけ"),
            ("dance", "ダンスまね"),
        ]

        STATUS_CHOICES = [
            ("playing", "プレイ中"),
            ("completed", "プレイ完了"),
            ("abandoned", "途中離脱"),
        ]

        token = models.UUIDField(
            default=uuid.uuid4,
            unique=True,
            editable=False,
            verbose_name="識別ID"
        )

        user = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            verbose_name="ユーザー"
        )

        game_round = models.PositiveIntegerField(
            default=1,
            verbose_name="育成回数"
        )

        action = models.CharField(
            max_length=20,
            choices=ACTION_CHOICES,
            verbose_name="ミニゲーム"
        )

        difficulty = models.CharField(
            max_length=20,
            default="easy",
            verbose_name="難易度"
        )

        status = models.CharField(
            max_length=20,
            choices=STATUS_CHOICES,
            default="playing",
            verbose_name="プレイ状態"
        )

        started_at = models.DateTimeField(
            default=timezone.now,
            verbose_name="開始日時"
        )

        ended_at = models.DateTimeField(
            null=True,
            blank=True,
            verbose_name="終了日時"
        )

        is_tutorial = models.BooleanField(
            default=False,
            verbose_name="チュートリアル"
        )

        stock_consumed = models.BooleanField(
            default=False,
            verbose_name="ストック消費済み"
        )

        score = models.PositiveIntegerField(
            default=0,
            verbose_name="スコア"
        )

        lives = models.PositiveSmallIntegerField(
            default=0,
            verbose_name="残りライフ"
        )

        result = models.CharField(
            max_length=100,
            blank=True,
            default="",
            verbose_name="結果"
        )

        success = models.BooleanField(
            default=False,
            verbose_name="成功"
        )

        growth_delta = models.DecimalField(
            max_digits=8,
            decimal_places=4,
            default=0,
            verbose_name="成長度変化"
        )

        def duration_seconds(self):
            if self.ended_at is None:
                return None

            return max(
                0,
                int(
                    (
                            self.ended_at - self.started_at
                    ).total_seconds()
                )
            )

        duration_seconds.short_description = "経過時間（秒）"

        class Meta:
            verbose_name = "ミニゲーム記録"
            verbose_name_plural = "ミニゲーム記録"

            ordering = ["-started_at"]

            constraints = [
                models.UniqueConstraint(
                    fields=["user"],
                    condition=models.Q(status="playing"),
                    name="realtime_one_active_minigame"
                )
            ]

        def __str__(self):
            return (
                f"{self.user} - "
                f"{self.get_action_display()}"
            )