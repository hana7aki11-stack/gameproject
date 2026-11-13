from django.db import models
from django.contrib.auth.models import User


class SaveData(models.Model):

    has_started_game = models.BooleanField(
        default=False,
        verbose_name='ニューゲーム開始済み'
    )

    # =========================
    # ユーザー
    # =========================
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='ユーザー'
    )



    # =========================
    # キャラクターの基本ステータス
    # =========================
    satisfaction = models.IntegerField(
        default=50,
        verbose_name='満足度'
    )

    energy = models.IntegerField(
        default=50,
        verbose_name='体力'
    )

    growth = models.IntegerField(
        default=0,
        verbose_name='成長度'
    )

    fullness = models.IntegerField(
        default=50,
        verbose_name='満腹度'
    )

    # =========================
    # ゲーム進行状況
    # =========================

    # 何回目の育成か（1から始まる。新しい育成を始めるたびに+1）
    game_round = models.IntegerField(default=1, verbose_name='育成回数')

    turn = models.IntegerField(
        default=1,
        verbose_name='ターン'
    )

    remaining_time = models.IntegerField(
        default=12,
        verbose_name='残り時間'
    )

    # =========================
    # プレイ回数・食事回数
    # =========================
    play_count = models.IntegerField(
        default=0,
        verbose_name='プレイ回数'
    )

    healthy_food_count = models.IntegerField(
        default=0,
        verbose_name='健康的な食事回数'
    )

    snack_count = models.IntegerField(
        default=0,
        verbose_name='おやつ回数'
    )

    # =========================
    # プレイ時間・セッション
    # =========================
    total_play_seconds = models.IntegerField(
        default=0,
        verbose_name='総プレイ時間（秒）'
    )

    play_session_count = models.IntegerField(
        default=0,
        verbose_name='プレイセッション数'
    )

    # =========================
    # 各行動の選択回数
    # =========================
    action_rest_count = models.IntegerField(
        default=0,
        verbose_name='「休む」選択回数'
    )

    action_ball_count = models.IntegerField(
        default=0,
        verbose_name='「ボールキャッチ」選択回数'
    )

    action_food_count = models.IntegerField(
        default=0,
        verbose_name='「好きなごはん選び」選択回数'
    )

    action_dodge_count = models.IntegerField(
        default=0,
        verbose_name='「障害物よけ」選択回数'
    )

    action_dance_count = models.IntegerField(
        default=0,
        verbose_name='「ダンスまね」選択回数'
    )

    action_timing_count = models.IntegerField(
        default=0,
        verbose_name='「火加減チャレンジ」選択回数'
    )

    action_count_count = models.IntegerField(
        default=0,
        verbose_name='「食材かぞえ」選択回数'
    )

    action_next_day_count = models.IntegerField(
        default=0,
        verbose_name='「次の日へ」選択回数'
    )

    # =========================
    # 育成結果
    # =========================
    clear_count = models.IntegerField(
        default=0,
        verbose_name='育成クリア回数'
    )

    game_over_count = models.IntegerField(
        default=0,
        verbose_name='ゲームオーバー回数'
    )

    clear_time_seconds = models.IntegerField(
        default=0,
        verbose_name='クリア時間（秒）'
    )

    # =========================
    # 育成開始日時
    # =========================
    play_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='育成開始日時'
    )

    # =========================
    # ボールキャッチ
    # =========================
    minigame_ball_play = models.IntegerField(
        default=0,
        verbose_name='ボールキャッチ プレイ回数'
    )

    minigame_ball_success = models.IntegerField(
        default=0,
        verbose_name='ボールキャッチ 成功回数'
    )

    # =========================
    # ごはん選び
    # =========================
    minigame_food_play = models.IntegerField(
        default=0,
        verbose_name='ごはん選び プレイ回数'
    )

    minigame_food_success = models.IntegerField(
        default=0,
        verbose_name='ごはん選び 成功回数'
    )

    # =========================
    # 障害物よけ
    # =========================
    minigame_dodge_play = models.IntegerField(
        default=0,
        verbose_name='障害物よけ プレイ回数'
    )

    minigame_dodge_success = models.IntegerField(
        default=0,
        verbose_name='障害物よけ 成功回数'
    )

    # =========================
    # ダンスまね
    # =========================
    minigame_dance_play = models.IntegerField(
        default=0,
        verbose_name='ダンスまね プレイ回数'
    )

    minigame_dance_success = models.IntegerField(
        default=0,
        verbose_name='ダンスまね 成功回数'
    )

    # =========================
    # 火加減チャレンジ
    # =========================
    minigame_timing_play = models.IntegerField(
        default=0,
        verbose_name='火加減チャレンジ プレイ回数'
    )

    minigame_timing_success = models.IntegerField(
        default=0,
        verbose_name='火加減チャレンジ 成功回数'
    )

    # =========================
    # 食材かぞえ
    # =========================
    minigame_count_play = models.IntegerField(
        default=0,
        verbose_name='食材かぞえ プレイ回数'
    )

    minigame_count_success = models.IntegerField(
        default=0,
        verbose_name='食材かぞえ 成功回数'
    )

    # =========================
    # キャラクター・部屋
    # =========================
    character_state = models.CharField(
        max_length=20,
        default='normal',
        verbose_name='キャラクター状態'
    )

    room_wallpaper = models.CharField(
        max_length=50,
        default='room-default',
        verbose_name='部屋の壁紙'
    )

    # =========================
    # アイテム
    # =========================
    items = models.JSONField(
        default=list,
        verbose_name='所持アイテム'
    )

    placed_items = models.JSONField(
        default=list,
        verbose_name='配置アイテム'
    )

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = 'ゲームデータ'
        verbose_name_plural = 'ゲームデータ'

    # チュートリアル進行（0=イントロ前, 1〜3=チュートリアル中, 4=完了）
    tutorial_step = models.IntegerField(default=0, verbose_name='チュートリアル進行')

    # まだ持ち物一覧で確認していない新規アイテム
    new_items = models.JSONField(default=list, verbose_name='未確認アイテム')

    # 成長段階のお知らせ表示済み段階
    notified_stage = models.IntegerField(
        default=0,
        verbose_name='通知済み成長段階'
    )


class ActionLog(models.Model):

    # どのユーザーの記録か
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='ユーザー'
    )


    # この行動が何回目の育成のものか
    game_round = models.IntegerField(default=1, verbose_name='育成回数')

    # 何をしたか
    action = models.CharField(
        max_length=50,
        verbose_name='行動'
    )

    # 行動の日時
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='日時'
    )

    # 行動時のターン数
    turn = models.IntegerField(
        default=1,
        verbose_name='ターン'
    )

    # 行動時のパラメータ（行動後の値）
    energy = models.IntegerField(default=50, verbose_name='体力')
    fullness = models.IntegerField(default=50, verbose_name='満腹度')
    satisfaction = models.IntegerField(default=50, verbose_name='満足度')
    growth = models.IntegerField(default=0, verbose_name='成長度')

    # ミニゲームの結果（スコア・ライフなど）
    result = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name='結果'
    )

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"

    class Meta:
        verbose_name = '行動ログ'
        verbose_name_plural = '行動ログ'
        ordering = ['-timestamp']  # 新しい順に並べる