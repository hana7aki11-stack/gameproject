from django.contrib import admin
from django.utils import timezone
from .models import SaveData, ActionLog, PlaySession, ClearLog


def format_duration(seconds):
    seconds = int(seconds or 0)
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    if h:
        return f"{h}時間{m}分{s}秒"
    if m:
        return f"{m}分{s}秒"
    return f"{s}秒"


@admin.register(PlaySession)
class PlaySessionAdmin(admin.ModelAdmin):

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

    readonly_fields = (
        'user',
        'game_round',
        'started_at',
        'last_seen_at',
        'logged_out_at',
        'page_views',
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

@admin.register(ClearLog)
class ClearLogAdmin(admin.ModelAdmin):

    list_display = (
        'user', 'clear_number_text', 'game_round',
        'play_time_text', 'elapsed_text', 'turns', 'cleared_at',
    )
    list_filter = ('user',)
    search_fields = ('user__username',)
    ordering = ('user', 'clear_number')

    readonly_fields = (
        'user', 'game_round', 'clear_number', 'cleared_at',
        'play_seconds', 'elapsed_seconds', 'turns',
    )

    @admin.display(description='クリア回数', ordering='clear_number')
    def clear_number_text(self, obj):
        return f"{obj.clear_number}回目"

    @admin.display(description='クリアまでのプレイ時間')
    def play_time_text(self, obj):
        return format_duration(obj.play_seconds)

    @admin.display(description='育成開始からの経過時間')
    def elapsed_text(self, obj):
        return format_duration(obj.elapsed_seconds)



@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):

    list_display = (
        'user', 'game_round', 'action', 'turn', 'result',
        'energy', 'fullness', 'satisfaction', 'growth', 'timestamp_text',
    )


    search_fields = (
        'user__username',
        'action',
    )

    list_filter = (
        'game_round',
        'action',
        'user',
    )

    ordering = ('-timestamp',)


    @admin.display(description='行動日時', ordering='timestamp')
    def timestamp_text(self, obj):
        from django.utils import timezone
        return timezone.localtime(obj.timestamp).strftime('%Y年%m月%d日 %H:%M:%S')


    readonly_fields = (
        'user',
        'game_round',
        'action',
        'turn',
        'energy',
        'fullness',
        'satisfaction',
        'growth',
        'result',
        'timestamp',
    )


@admin.register(SaveData)
class SaveDataAdmin(admin.ModelAdmin):

    # ========================================
    # 一覧画面に表示する項目
    # ========================================
    list_display = (
        'user',
        'game_round',
        'growth',
        'energy',
        'satisfaction',
        'fullness',
        'turn',
        'play_count',
        'clear_count',
        'game_over_count',
    )

    # ========================================
    # 検索
    # ========================================
    search_fields = (
        'user__username',
    )

    # ========================================
    # 絞り込み
    # ========================================
    list_filter = (
        'character_state',
        'room_wallpaper',
    )

    # ========================================
    # 詳細画面の項目をグループ化
    # ========================================
    fieldsets = (

        (
            'ユーザー情報',
            {
                'fields': (
                    'user',
                )
            }
        ),

        (
            'キャラクターの基本ステータス',
            {
                'fields': (
                    'satisfaction',
                    'energy',
                    'growth',
                    'fullness',
                )
            }
        ),

        (
            'ゲーム進行状況',
            {
                'fields': (
                    'turn',
                    'remaining_time',
                )
            }
        ),

        (
            'プレイ状況',
            {
                'fields': (
                    'play_count',
                    'game_round',
                    'play_session_count',
                    'round_play_seconds',
                    'play_started_at',
                )
            }
        ),

        (
            '食事関連',
            {
                'fields': (
                    'healthy_food_count',
                    'snack_count',
                )
            }
        ),

        (
            '行動の選択回数',
            {
                'fields': (
                    'action_rest_count',
                    'action_ball_count',
                    'action_food_count',
                    'action_dodge_count',
                    'action_dance_count',
                    'action_timing_count',
                    'action_count_count',
                    'action_next_day_count',
                )
            }
        ),

        (
            '育成結果',
            {
                'fields': (
                    'clear_count',
                    'game_over_count',
                    'clear_time_seconds',
                )
            }
        ),

        (
            'ボールキャッチ',
            {
                'fields': (
                    'minigame_ball_play',
                    'minigame_ball_success',
                )
            }
        ),

        (
            'ごはん選び',
            {
                'fields': (
                    'minigame_food_play',
                    'minigame_food_success',
                )
            }
        ),

        (
            '障害物よけ',
            {
                'fields': (
                    'minigame_dodge_play',
                    'minigame_dodge_success',
                )
            }
        ),

        (
            'ダンスまね',
            {
                'fields': (
                    'minigame_dance_play',
                    'minigame_dance_success',
                )
            }
        ),

        (
            '火加減チャレンジ',
            {
                'fields': (
                    'minigame_timing_play',
                    'minigame_timing_success',
                )
            }
        ),

        (
            '食材かぞえ',
            {
                'fields': (
                    'minigame_count_play',
                    'minigame_count_success',
                )
            }
        ),

        (
            'キャラクター・部屋',
            {
                'fields': (
                    'character_state',
                    'room_wallpaper',
                )
            }
        ),

        (
            'アイテム',
            {
                'fields': (
                    'items',
                    'placed_items',
                )
            }
        ),
    )