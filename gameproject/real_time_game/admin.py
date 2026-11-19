from django.contrib import admin
from django.utils import timezone
from .models import (
    RealTimeSaveData,
    RealTimeActionLog,
    RealTimePlaySession,
    RealTimeClearLog,
    RealTimeSitterLog,
)


# =========================
# 時間の表示を整える
# =========================
def format_duration(seconds):
    seconds = int(seconds or 0)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)

    if hours:
        return f'{hours}時間{minutes}分{secs}秒'

    if minutes:
        return f'{minutes}分{secs}秒'

    return f'{secs}秒'


# =========================
# リアルタイム育成データ
# =========================
@admin.register(RealTimeSaveData)
class RealTimeSaveDataAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'game_round',
        'status',
        'growth',
        'energy',
        'satisfaction',
        'fullness',
        'sitter_started_at',
        'last_updated_at',
    )

    search_fields = ('user__username',)
    list_filter = ('status', 'character_state')

    readonly_fields = tuple(
        f.name for f in RealTimeSaveData._meta.fields
        if f.name != 'id'
    )


# =========================
# リアルタイム行動ログ
# =========================
@admin.register(RealTimeActionLog)
class RealTimeActionLogAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'game_round',
        'action',
        'result',
        'growth',
        'growth_delta',
        'natural_growth_delta',
        'timestamp',
    )

    list_filter = ('game_round', 'action', 'user')
    search_fields = ('user__username', 'action')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'

    readonly_fields = tuple(
        f.name for f in RealTimeActionLog._meta.fields
        if f.name != 'id'
    )


# =========================
# リアルタイムプレイログ
# =========================
@admin.register(RealTimePlaySession)
class RealTimePlaySessionAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'game_round',
        'start_text',
        'end_text',
        'duration_text',
        'logged_out_text',
        'page_views_text',
    )

    list_filter = ('user', 'game_round')
    search_fields = ('user__username',)
    ordering = ('-started_at',)
    date_hierarchy = 'started_at'

    readonly_fields = tuple(
        f.name for f in RealTimePlaySession._meta.fields
        if f.name != 'id'
    )

    @admin.display(description='プレイ開始', ordering='started_at')
    def start_text(self, obj):
        return timezone.localtime(
            obj.started_at
        ).strftime('%Y/%m/%d %H:%M:%S')

    @admin.display(description='プレイ終了（最終通信）', ordering='last_seen_at')
    def end_text(self, obj):
        return timezone.localtime(
            obj.last_seen_at
        ).strftime('%Y/%m/%d %H:%M:%S')

    @admin.display(description='プレイ時間')
    def duration_text(self, obj):
        return format_duration(obj.duration_seconds())

    @admin.display(description='セッション終了時刻', ordering='logged_out_at')
    def logged_out_text(self, obj):
        if obj.logged_out_at is None:
            return '（未記録）'

        return timezone.localtime(
            obj.logged_out_at
        ).strftime('%Y/%m/%d %H:%M:%S')

    @admin.display(description='画面表示回数', ordering='page_views')
    def page_views_text(self, obj):
        return obj.page_views

# =========================
# リアルタイムクリア記録
# =========================
@admin.register(RealTimeClearLog)
class RealTimeClearLogAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'game_round',
        'clear_number',
        'cleared_at',
        'play_time_text',
        'elapsed_text',
        'natural_growth_total',
        'active_growth_total',
        'sitter_time_text',
    )

    list_filter = ('user',)
    search_fields = ('user__username',)
    ordering = ('-cleared_at',)

    readonly_fields = tuple(
        f.name for f in RealTimeClearLog._meta.fields
        if f.name != 'id'
    )

    @admin.display(description='プレイ時間')
    def play_time_text(self, obj):
        return format_duration(obj.play_seconds)

    @admin.display(description='育成経過時間')
    def elapsed_text(self, obj):
        return format_duration(obj.elapsed_seconds)

    @admin.display(description='シッター利用時間')
    def sitter_time_text(self, obj):
        return format_duration(obj.sitter_seconds)


# =========================
# リアルタイムシッター利用記録
# =========================
@admin.register(RealTimeSitterLog)
class RealTimeSitterLogAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'game_round',
        'started_at',
        'ended_at',
        'duration_text',
        'auto_ended',
    )

    list_filter = ('auto_ended', 'user')
    search_fields = ('user__username',)
    ordering = ('-started_at',)

    readonly_fields = tuple(
        f.name for f in RealTimeSitterLog._meta.fields
        if f.name != 'id'
    )

    @admin.display(description='利用時間')
    def duration_text(self, obj):
        if obj.ended_at is None:
            return '利用中'
        return format_duration(obj.duration_seconds())


# =========================
# ミニゲーム記録
# =========================

from .models import RealTimeMinigameSession


@admin.register(RealTimeMinigameSession)
class RealTimeMinigameSessionAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "game_round",
        "action",
        "difficulty",
        "status",
        "started_at",
        "ended_at",
        "duration_seconds",
        "score",
        "lives",
        "success",
        "growth_delta",
        "is_tutorial",
        "stock_consumed",
    )

    list_filter = (
        "action",
        "difficulty",
        "status",
        "success",
        "is_tutorial",
    )

    search_fields = (
        "user__username",
    )

    ordering = ("-started_at",)

    readonly_fields = (
        "token",
        "user",
        "game_round",
        "action",
        "difficulty",
        "status",
        "started_at",
        "ended_at",
        "is_tutorial",
        "stock_consumed",
        "score",
        "lives",
        "result",
        "success",
        "growth_delta",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
