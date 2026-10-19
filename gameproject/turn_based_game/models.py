from django.db import models
from django.contrib.auth.models import User


class SaveData(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    satisfaction = models.IntegerField(default=50)
    energy = models.IntegerField(default=50)
    growth = models.IntegerField(default=0)
    fullness = models.IntegerField(default=50)

    turn = models.IntegerField(default=1)
    remaining_time = models.IntegerField(default=6)

    play_count = models.IntegerField(default=0)
    healthy_food_count = models.IntegerField(default=0)
    snack_count = models.IntegerField(default=0)

    # 総プレイ時間（秒単位で累積）
    total_play_seconds = models.IntegerField(default=0)

    # プレイ回数（セッション開始のたびに+1）
    play_session_count = models.IntegerField(default=0)

    # 各行動の選択回数
    action_rest_count = models.IntegerField(default=0)  # 休む
    action_ball_count = models.IntegerField(default=0)  # ボールキャッチ
    action_food_count = models.IntegerField(default=0)  # 好きなごはん選び
    action_dodge_count = models.IntegerField(default=0)  # 障害物よけ
    action_dance_count = models.IntegerField(default=0)  # ダンスまね
    action_timing_count = models.IntegerField(default=0)  # 火加減チャレンジ
    action_count_count = models.IntegerField(default=0)  # 食材かぞえ
    action_next_day_count = models.IntegerField(default=0)  # 次の日へ

    # 育成完了回数（growth >= 100 になった回数）
    clear_count = models.IntegerField(default=0)

    # ゲームオーバー回数（energy <= 0 になった回数）
    game_over_count = models.IntegerField(default=0)

    # ゲームクリアまでの時間（秒単位、最初のプレイ開始から育成完了まで）
    clear_time_seconds = models.IntegerField(default=0)

    # 育成開始日時（リセット時にリセットされる）
    play_started_at = models.DateTimeField(null=True, blank=True)

    # ミニゲームごとのプレイ回数と成功回数
    minigame_ball_play = models.IntegerField(default=0)
    minigame_ball_success = models.IntegerField(default=0)

    minigame_food_play = models.IntegerField(default=0)
    minigame_food_success = models.IntegerField(default=0)  # ライフ1以上で成功とする

    minigame_dodge_play = models.IntegerField(default=0)
    minigame_dodge_success = models.IntegerField(default=0)

    minigame_dance_play = models.IntegerField(default=0)
    minigame_dance_success = models.IntegerField(default=0)  # clearで成功

    minigame_timing_play = models.IntegerField(default=0)
    minigame_timing_success = models.IntegerField(default=0)

    minigame_count_play = models.IntegerField(default=0)
    minigame_count_success = models.IntegerField(default=0)


    character_state = models.CharField(
        max_length=20,
        default='normal'
    )

    room_wallpaper = models.CharField(
        max_length=50,
        default='room-default'
    )

    items = models.JSONField(default=list)
    placed_items = models.JSONField(default=list)

    def __str__(self):
        return self.user.username