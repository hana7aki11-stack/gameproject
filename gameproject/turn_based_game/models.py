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